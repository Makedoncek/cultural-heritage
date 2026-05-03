"""Інкапсуляція Cloudinary SDK для upload/delete фото."""
import cloudinary
import cloudinary.uploader

UPLOAD_FOLDER = 'cultural-heritage/photos'


def _build_url(public_id: str, transformation: str) -> str:
    cloud_name = cloudinary.config().cloud_name or ''
    return f'https://res.cloudinary.com/{cloud_name}/image/upload/{transformation}/{public_id}'


def upload_photo(file) -> dict:
    """Завантажує файл у Cloudinary і повертає dict з public_id, image_url, thumbnail_url."""
    response = cloudinary.uploader.upload(
        file,
        folder=UPLOAD_FOLDER,
        resource_type='image',
    )
    public_id = response['public_id']
    return {
        'public_id': public_id,
        'image_url': _build_url(public_id, 'f_auto,q_auto'),
        'thumbnail_url': _build_url(public_id, 'w_300,h_200,c_fill,f_auto,q_auto'),
    }


def delete_photo(public_id: str) -> None:
    """Видаляє файл з Cloudinary за public_id."""
    cloudinary.uploader.destroy(public_id)
