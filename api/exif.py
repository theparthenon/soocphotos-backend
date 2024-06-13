from exiftool import ExifToolHelper


class Tags:
    """Class of wanted EXIF tags."""

    RATING = "Rating"
    IMAGE_HEIGHT = "ImageHeight"
    IMAGE_WIDTH = "ImageWidth"
    DATE_TIME = "EXIF: DateTime"
    DATE_TIME_ORIGINAL = "EXIF: DateTimeOriginal"
    QUICKTIME_CREATE_DATE = "QuickTime:CreateDate"
    QUICKTIME_DURATION = "QuickTime:Duration"
    LATITUDE = "Composite:GPSLatitude"
    LONGITUDE = "Composite:GPSLongitude"
    GPS_DATE_TIME = "Composite:GPSDateTime"
    FILE_SIZE = "File:FileSize"


with ExifToolHelper() as et:
    for d in et.get_metadata(
        "/Users/larstonblake/Github/soocphotos/data/consume/img20200307_17533126 copy.tif"
    ):
        for k, v in d.items():
            print(f"Dict: {k} = {v}")

# with ExifToolHelper() as et:
#     metadata = et.get_tags(
#         "/Users/larstonblake/Github/soocphotos/data/IMG_0034.JPG",
#         tags=[
#             Tags.RATING,
#             Tags.IMAGE_HEIGHT,
#             Tags.IMAGE_WIDTH,
#             Tags.QUICKTIME_CREATE_DATE,
#             Tags.QUICKTIME_DURATION,
#             Tags.LATITUDE,
#             Tags.LONGITUDE,
#             Tags.GPS_DATE_TIME,
#             Tags.FILE_SIZE,
#         ],
#     )

#     print(metadata)
