"""Classify faces and cluster."""

import datetime
import uuid
import numpy as np
import pytz
import seaborn as sns
from bulk_update.helper import bulk_update
from hdbscan import HDBSCAN
from sklearn.decomposition import PCA
from sklearn.neural_network import MLPClassifier

from django.core.paginator import Paginator
from django.db.models import Q
from django_q.tasks import AsyncTask

from api.face_cluster_manager import ClusterManager
from api.models import Face, Job, Person
from api.models.cluster import Cluster, UNKNOWN_CLUSTER_ID
from api.models.person import get_unknown_person
from api.models.user import User, get_deleted_user
from api.utils import logger

FACE_CLASSIFY_COLUMNS = [
    "id",
    "cluster",
    "person",
    "person_label_is_inferred",
    "person_label_probability",
]


def cluster_faces(user, inferred=True):
    """Clusters faces for a given user."""

    persons = [p.id for p in Person.objects.filter(faces__photo__owner=user).distinct()]
    p2c = dict(zip(persons, sns.color_palette(n_colors=len(persons)).as_hex()))

    face_encoding = []
    faces = Face.objects.filter(photo__owner=user)
    paginator = Paginator(faces, 5000)

    for page in range(1, paginator.num_pages + 1):
        for face in paginator.page(page).object_list:
            if ((not face.person_label_is_inferred) or inferred) and face.encoding:
                face_encoding.append(face.get_encoding_array())

    pca = PCA(n_components=3)
    vis_all = pca.fit_transform(face_encoding)

    res = []

    for face, vis in zip(faces, vis_all):
        res.append(
            {
                "person_id": face.person.id,
                "person_name": face.person.name,
                "person_label_is_inferred": face.person_label_is_inferred,
                "color": p2c[face.person.id],
                "face_url": face.image.url,
                "value": {"x": vis[0], "y": vis[1], "size": vis[2]},
            }
        )

    return res


def cluster_all_faces(user, job_id) -> bool:
    """Clusters all faces for a given user."""

    if Job.objects.filter(job_id=job_id).exists():
        job = Job.objects.get(job_id=job_id)
        job.started_at = datetime.datetime.now().replace(tzinfo=pytz.utc)
    else:
        job = Job.objects.create(
            started_by=user,
            job_id=job_id,
            queued_at=datetime.datetime.now().replace(tzinfo=pytz.utc),
            started_at=datetime.datetime.now().replace(tzinfo=pytz.utc),
            job_type=Job.JOB_CLUSTER_ALL_FACES,
        )

    job.result = {"progress": {"current": 0, "target": 1}}

    job.save()

    try:
        delete_clustered_people(user)
        delete_clusters(user)
        delete_persons_without_faces()
        target_count: int = create_all_clusters(user, job)

        job.finished = True
        job.failed = False
        job.finished_at = datetime.datetime.now().replace(tzinfo=pytz.utc)
        job.result = {"progress": {"current": target_count, "target": target_count}}
        job.save()

        train_job_id = uuid.uuid4()
        AsyncTask(train_faces, user, train_job_id).run()

        return True
    except BaseException as e:  # pylint: disable=broad-except
        logger.exception("An error occurred: ")
        print(f"[ERR]: {e}.")

        job.failed = True
        job.finished = True
        job.finished_at = datetime.datetime.now().replace(tzinfo=pytz.utc)
        job.save()

        return False


def create_all_clusters(user: User, job: Job = None) -> int:
    """Creates all clusters for a given user."""

    all_clusters: list[Cluster] = []
    face: Face
    logger.info("Creating clusters")

    data = {"all": {"encoding": [], "id": [], "person_id": [], "person_labeled": []}}

    for face in Face.objects.filter(photo__owner=user).prefetch_related("person"):
        data["all"]["encoding"].append(face.get_encoding_array())
        data["all"]["id"].append(face.id)

    target_count = len(data["all"]["id"])

    if target_count == 0:
        return target_count

    min_cluster_size = 2

    if (
        user.min_cluster_size == 0
        or user.min_cluster_size == 1
        or user.min_cluster_size is None
    ):
        if target_count > 1000:
            min_cluster_size = 4
        if target_count > 10000:
            min_cluster_size = 8
        if target_count > 100000:
            min_cluster_size = 16
    else:
        min_cluster_size = user.min_cluster_size

    min_samples = 1

    if user.min_samples > 0:
        min_samples = user.min_samples

    clt = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        cluster_selection_epsilon=user.cluster_selection_epsilon,
        metric="euclidean",
    )

    logger.info("Before finding clusters")
    clt.fit(np.array(data["all"]["encoding"]))
    logger.info("After finding clusters")

    label_ids = np.unique(clt.labels_)
    label_id: np.intp
    commit_time = datetime.datetime.now() + datetime.timedelta(seconds=5)
    count: int = 0
    max_len: int = len(str(np.size(label_ids)))
    sorted_indexes: dict[int, np.ndarray] = dict()
    cluster_count: int = 0
    cluster_id: int

    for label_id in label_ids:
        idxs = np.where(clt.labels_ == label_id)[0]
        sorted_indexes[label_id] = idxs

    logger.info("Found %d clusters.", len(sorted_indexes))

    for label_id in sorted(
        sorted_indexes, key=lambda key: np.size(sorted_indexes[key]), reverse=True
    ):
        if label_id != UNKNOWN_CLUSTER_ID:
            cluster_count = cluster_count + 1
            cluster_id = cluster_count

        else:
            cluster_id = label_id

        face_array: list[Face] = []
        face_id_list: list[int] = []

        for i in sorted_indexes[label_id]:
            count = count + 1
            face_id = data["all"]["id"][i]
            face_id_list.append(face_id)

        face_array = Face.objects.filter(pk__in=face_id_list)
        new_clusters: list[Cluster] = ClusterManager.try_add_cluster(
            user, cluster_id, face_array, max_len
        )

        if commit_time < datetime.datetime.now() and job is not None:
            job.result = {"progress": {"current": count, "target": target_count}}
            job.save()
            commit_time = datetime.datetime.now() + datetime.timedelta(seconds=5)

        all_clusters.extend(new_clusters)

    print(f"Created {len(all_clusters)} clusters.")


def delete_persons_without_faces():
    """Delete all existing Person records that have no associated Face records"""

    print("Deleting all people without faces.")
    Person.objects.filter(faces=None, kind=Person.KIND_USER).delete()


def delete_clusters(user: User):
    """Delete all existing cluster records."""

    print("Deleting all clusters")
    Cluster.objects.filter(Q(owner=user)).delete()
    Cluster.objects.filter(Q(owner=None)).delete()
    Cluster.objects.filter(Q(owner=get_deleted_user())).delete()


def delete_clustered_people(user: User):
    """Delete all existing Person records of type CLUSTER."""

    print("Deleting all clustered people.")
    Person.objects.filter(kind=Person.KIND_CLUSTER, cluster_owner=user).delete()
    Person.objects.filter(kind=Person.KIND_UNKNOWN, cluster_owner=user).delete()
    Person.objects.filter(cluster_owner=None).delete()
    Person.objects.filter(cluster_owner=get_deleted_user()).delete()


def train_faces(user: User, job_id) -> bool:
    """Train faces for a given user."""

    if Job.objects.filter(job_id=job_id).exists():
        job = Job.objects.get(job_id=job_id)
        job.started_at = datetime.datetime.now().replace(tzinfo=pytz.utc)

    else:
        job = Job.objects.create(
            started_by=user,
            job_id=job_id,
            queued_at=datetime.datetime.now().replace(tzinfo=pytz.utc),
            started_at=datetime.datetime.now().replace(tzinfo=pytz.utc),
            job_type=Job.JOB_TRAIN_FACES,
        )

    job.result = {"progress": {"current": 1, "target": 2}}
    job.save()

    unknown_person: Person = get_unknown_person(owner=user)

    try:
        data_known = {"encoding": [], "id": []}
        data_unknown = {"encoding": [], "id": []}
        face: Face

        for face in Face.objects.filter(Q(photo__owner=user)).prefetch_related(
            "person"
        ):
            person: Person = face.person
            unknown = (
                face.person_label_is_inferred is not False
                or person.kind == Person.KIND_CLUSTER
                or person.kind == Person.KIND_UNKNOWN
            )

            if unknown:
                data_unknown["encoding"].append(face.get_encoding_array())
                data_unknown["id"].append(face.id if unknown else face.person.id)

            else:
                data_known["encoding"].append(face.get_encoding_array())
                data_known["id"].append(face.id if unknown else face.person.id)

        cluster: Cluster

        for cluster in Cluster.objects.filter(owner=user):
            if cluster.person.kind == Person.KIND_CLUSTER:
                data_known["encoding"].append(cluster.get_mean_encoding_array())
                data_known["id"].append(cluster.person.id)

        if len(data_known["id"]) == 0:
            logger.info("No labeled faces found.")
            job.finished = True
            job.failed = False
            job.result = {"progress": {"current": 2, "target": 2}}
            job.finished_at = datetime.datetime.now().replace(tzinfo=pytz.utc)
            job.save()

        else:
            logger.info("Before fitting")
            clf = MLPClassifier(
                solver="adam", alpha=1e-5, random_state=1, max_iter=1000
            ).fit(np.array(data_known["encoding"]), np.array(data_known["id"]))
            logger.info("After fitting")

            target_count = len(data_unknown["id"])
            logger.info("Number of Cluster: %d.", target_count)

            if target_count != 0:
                pages_encoding = [
                    data_unknown["encoding"][i : i + 100]
                    for i in range(0, len(data_unknown["encoding"]), 100)
                ]
                pages_id = [
                    data_unknown["id"][i : i + 100]
                    for i in range(0, len(data_unknown["encoding"]), 100)
                ]

                for idx, page in enumerate(pages_encoding):
                    page_id = pages_id[idx]
                    pages_of_faces = Face.objects.filter(id__in=page_id).all()
                    pages_of_faces = sorted(
                        pages_of_faces,
                        key=lambda x: page_id.index(  # pylint: disable=cell-var-from-loop
                            x.id
                        ),
                    )
                    face_encodings_unknown_np = np.array(page)
                    probs = clf.predict_proba(face_encodings_unknown_np)
                    commit_time = datetime.datetime.now() + datetime.timedelta(
                        seconds=5
                    )
                    face_stack == []  # pylint: disable=pointless-statement

                    for idx, (face, probability_array) in enumerate(
                        zip(pages_of_faces, probs)
                    ):
                        if (
                            face.person is unknown_person
                            or face.person.kind == Person.KIND_UNKNOWN
                        ):
                            face.person_label_is_inferred = False

                        else:
                            face.person_label_is_inferred = True

                        probability: np.float64 = 0

                        highest_probability = max(probability_array)
                        highest_probability_person = 0

                        for i, target in enumerate(clf.classes_):
                            if highest_probability == probability_array[i]:
                                highest_probability_person = target

                            if target == face.person.id:
                                probability = probability_array[i]

                        face.person = Person.objects.get(id=highest_probability_person)

                        if (
                            probability > user.confidence_unknown_face
                            or user.confidence_unknown_face == 0
                        ) and face.person.id != unknown_person.id:
                            face.person_label_is_inferred = True
                            face.person_label_probability = highest_probability

                        else:
                            face.person_label_is_inferred = False
                            face.person_label_probability = probability

                        face_stack.append(face)

                        if commit_time < datetime.datetime.now():
                            job.result = {
                                "progress": {"current": idx + 1, "target": target_count}
                            }
                            job.save()
                            commit_time = datetime.datetime.now() + datetime.timedelta(
                                seconds=5
                            )

                        if len(face_stack) > 200:
                            bulk_update(face_stack, update_fields=FACE_CLASSIFY_COLUMNS)
                            face_stack = []

                    bulk_update(face_stack, update_fields=FACE_CLASSIFY_COLUMNS)

            job.finished = True
            job.failed = False
            job.result = {"progress": {"current": target_count, "target": target_count}}
            job.finished_at = datetime.datetime.now().replace(tzinfo=pytz.utc)
            job.save()

            return True

    except BaseException as e:  # pylint: disable=broad-except
        logger.exception("An error occurred")
        print(f"[ERR]: {format(e)}")
        job.failed = True
        job.finished = True
        job.finished_at = datetime.datetime.now().replace(tzinfo=pytz.utc)
        job.save()

        return False
