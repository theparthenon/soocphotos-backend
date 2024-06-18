"""Register models for Django's admin area."""

from django.contrib import admin
from django_q.tasks import AsyncTask

from .models import Cluster, Face, File, Job, Person, Photos, User


def deduplicate_faces_function(queryset):
    """
    Deduplicates faces in a queryset of photos by comparing the bounding boxes of the faces.

    Args:
        queryset (QuerySet): A queryset of photo objects.

    Returns:
        None

    This function iterates over each photo in the queryset and retrieves all the faces associated
    with the photo. It then checks if there are any faces that have similar bounding boxes. If
    there are, it categorizes the faces into two groups: faces with a person label and faces
    without a person label. It keeps the first face with a person label and deletes the rest. If
    there are no faces with a person label, it keeps the first face without a person label and
    deletes the rest. This process is repeated for all photos in the queryset.
    """

    for photo in queryset:
        # Get all faces in the photo
        faces = Face.objects.filter(photo=photo)
        # Check if there are any faces which have similar bounding boxes
        for face in faces:
            margin = int((face.location_right - face.location_left) * 0.05)
            similar_faces = Face.objects.filter(
                photo=photo,
                location_top__lte=face.location_top + margin,
                location_top__gte=face.location_top - margin,
                location_right__lte=face.location_right + margin,
                location_right__gte=face.location_right - margin,
                location_bottom__lte=face.location_bottom + margin,
                location_bottom__gte=face.location_bottom - margin,
                location_left__lte=face.location_left + margin,
                location_left__gte=face.location_left - margin,
            )
            if len(similar_faces) > 1:
                # Divide between faces with a person label and faces without
                faces_with_person_label = []
                faces_without_person_label = []
                for similar_face in similar_faces:
                    if similar_face.person:
                        faces_with_person_label.append(similar_face)
                    else:
                        faces_without_person_label.append(similar_face)
                # If there are faces with a person label, keep the first one and delete the rest
                for similar_face in faces_with_person_label[1:]:
                    similar_face.delete()
                # If there are faces with a person label, delete all of them
                if len(faces_with_person_label) > 0:
                    for similar_face in faces_without_person_label:
                        similar_face.delete()
                # Otherwise, keep the first face and delete the rest
                else:
                    for similar_face in faces_without_person_label[1:]:
                        similar_face.delete()


class FaceDeduplication(admin.ModelAdmin):
    """Custom admin area for face deduplication."""

    actions = ["deduplicate_faces"]

    def deduplicate_faces(self, request, queryset):
        """
        Deduplicates faces in the given queryset asynchronously.
        Args:
            request (HttpRequest): The HTTP request object.
            queryset (QuerySet): The queryset of faces to deduplicate.
        Returns:
            None
        """

        AsyncTask(
            deduplicate_faces_function,
            queryset=queryset,
        ).run()


# Register your models here.
admin.site.register(Photos, FaceDeduplication)
admin.site.register(Person)
admin.site.register(Face)
admin.site.register(File)
admin.site.register(Cluster)
admin.site.register(Job)
admin.site.register(User)
