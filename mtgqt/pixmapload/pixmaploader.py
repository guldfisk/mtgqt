import typing as t
from concurrent.futures import Executor, ThreadPoolExecutor

from PIL import ImageQt, Image
from promise import Promise
from cachetools import cached, LRUCache

from PyQt5.QtGui import QPixmap

from mtgorp.models.persistent.printing import Printing

from mtgimg.load import Loader as ImageLoader
from mtgimg.interface import ImageRequest, pictureable, SizeSlug, Imageable


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

        self._default_images = {
            size_slug: QPixmap.fromImage(
                ImageQt.ImageQt(
                    self._image_loader.get_default_image(size_slug)
                )
            )
            for size_slug in
            SizeSlug
        }

    @cached(cache = LRUCache(maxsize = 64))
    def _get_pixmap(self, image_request: ImageRequest):
        image = self._image_loader.get_image(image_request = image_request).get()
        return QPixmap.fromImage(
            ImageQt.ImageQt(
                image
            )
        )

    def get_pixmap(
        self,
        pictured: pictureable = None,
        *,
        pictured_type: t.Union[t.Type[Printing], t.Type[Imageable]] = Printing,
        picture_name: t.Optional[str] = None,
        back: bool = False,
        crop: bool = False,
        size_slug: SizeSlug = SizeSlug.ORIGINAL,
        save: bool = True,
        cache_only: bool = False,
        image_request: ImageRequest = None,
    ) -> Promise[Image.Image]:
        _image_request = (
            ImageRequest(
                pictured = pictured,
                pictured_type = pictured_type,
                picture_name = picture_name,
                back = back,
                crop = crop,
                size_slug = size_slug,
                save = save,
                cache_only = cache_only,
            )
            if image_request is None else
            image_request
        )

        return Promise.resolve(
            self._pixmap_executor.submit(
                self._get_pixmap,
                _image_request,
            )
        )

    def get_default_pixmap(self, size_slug: SizeSlug = SizeSlug.ORIGINAL) -> QPixmap:
        return self._default_images[size_slug]
