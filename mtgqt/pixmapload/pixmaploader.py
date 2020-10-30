import typing as t
from concurrent.futures import Executor
from functools import lru_cache

from PIL import ImageQt, Image
from promise import Promise

from PyQt5.QtGui import QPixmap

from mtgorp.models.persistent.printing import Printing

from mtgimg.load import Loader
from mtgimg.interface import ImageRequest, pictureable, SizeSlug, Imageable, ImageLoader


class PixmapLoader(object):

    def __init__(
        self,
        *,
        imageable_executor: t.Union[Executor, int] = None,
        printing_executor: t.Union[Executor, int] = None,
        image_loader: ImageLoader = None,
        image_cache_size: t.Optional[int] = 64,
    ):
        self._image_loader = (
            Loader(
                imageable_executor = imageable_executor,
                printing_executor = printing_executor,
                image_cache_size = None,
            ) if image_loader is None else
            image_loader
        )

        self._default_images = {
            size_slug: self.image_to_pixmap(
                self._image_loader.get_default_image(size_slug)
            )
            for size_slug in
            SizeSlug
        }

        if image_cache_size is not None:
            self._get_pixmap = lru_cache(maxsize = image_cache_size)(self._get_pixmap)

    @property
    def image_loader(self) -> ImageLoader:
        return self._image_loader

    @classmethod
    def image_to_pixmap(cls, image: Image.Image) -> QPixmap:
        return QPixmap.fromImage(
            ImageQt.ImageQt(
                image
            )
        )

    def _get_pixmap(self, image_request: ImageRequest) -> Promise[QPixmap]:
        return self._image_loader.get_image(image_request = image_request).then(
            self.image_to_pixmap
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
    ) -> Promise[QPixmap]:
        return self._get_pixmap(
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

    def get_default_pixmap(self, size_slug: SizeSlug = SizeSlug.ORIGINAL) -> QPixmap:
        return self._default_images[size_slug]

    def stop(self) -> None:
        self._image_loader.stop()
