import typing as t
import os
from concurrent.futures import Executor, ThreadPoolExecutor

from PIL import ImageQt, Image
from promise import Promise
from PyQt5.QtGui import QPixmap

from mtgimg.load import Loader as ImageLoader, TaskAwaiter
from mtgimg.interface import ImageRequest, pictureable


class _PixmapConverter(object):

    def __init__(self):
        self._pixmaps = dict()  # type: t.Dict[ImageRequest, QPixmap]
        self._processing = TaskAwaiter()

    def get_pixmap(self, image_request: t.Optional[ImageRequest], image: Image.Image):
        try:
            return self._pixmaps[image_request]
        except KeyError:
            pass

        event, in_progress = self._processing.get_condition(image_request)

        if in_progress:
            event.wait()

            return self._pixmaps[image_request]

        if image_request and os.path.exists(image_request.path):
            pixmap = QPixmap(image_request.path)

        else:
            self._pixmaps[image_request] = pixmap = QPixmap.fromImage(
                ImageQt.ImageQt(
                    image
                )
            )

        self._pixmaps[image_request] = pixmap

        event.set_value(None)

        return pixmap


class PixmapLoader(object):

    def __init__(
        self,
        pixmap_executor: t.Union[Executor, int] = None,
        *,
        imageable_executor: t.Union[Executor, int] = None,
        printing_executor: t.Union[Executor, int] = None,
        image_loader: ImageLoader = None,
    ):
        self._image_loader = (
            ImageLoader(
                imageable_executor = imageable_executor,
                printing_executor = printing_executor,
            ) if image_loader is None else
            image_loader
        )

        self._pixmap_executor = (
            pixmap_executor
            if pixmap_executor is isinstance(pixmap_executor, Executor) else
            ThreadPoolExecutor(
                max_workers = pixmap_executor if isinstance(pixmap_executor, int) else 10
            )
        )

        self._pixmap_converter = _PixmapConverter()

        self._default_image = self._image_loader.get_default_image()

    def get_pixmap(
        self,
        pictured: pictureable = None,
        back: bool = False,
        crop: bool = False,
        image_request: ImageRequest = None
    ) -> Promise:

        _image_request = (
            ImageRequest(pictured, back = back, crop = crop)
            if image_request is None else
            image_request
        )

        return self._image_loader.get_image(
            image_request = _image_request,
        ).then(
            lambda image:
            self._pixmap_executor.submit(
                self._pixmap_converter.get_pixmap,
                _image_request,
                image,
            )
        )

    def get_default_pixmap(self) -> QPixmap:
        return self._pixmap_converter.get_pixmap(None, self._default_image)

    # return self._image_loader.get_default_image().then(
    # 	lambda image: self._pixmap_converter.get_pixmap(None, image)
    # )