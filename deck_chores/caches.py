from functools import lru_cache
from typing import Dict

from deck_chores.config import cfg


@lru_cache()
def get_image_labels(image_id: str) -> Dict[str, str]:
    if ':' in image_id:
        image_id = image_id.split(':')[1]
    return cfg.client.inspect_image(image_id)['Config'].get('Labels', {})


@lru_cache()
def get_image_labels_for_container(container_id: str) -> Dict[str, str]:
    image_id = cfg.client.inspect_container(container_id)['Image']
    return get_image_labels(image_id)


@lru_cache()
def get_filtered_image_labels_for_container(container_id: str) -> Dict[str, str]:
    image_id = cfg.client.inspect_container(container_id)['Image']
    labels = get_image_labels(image_id)
    return {k: v for k, v in labels.items() if k.startswith(cfg.label_ns)}
