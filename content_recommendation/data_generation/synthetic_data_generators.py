"""
Functions to generate synthetic basic user attributes and media metadata
dictionaries based on configuration settings.
"""
import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any

# --- Constants ---
TARGET_ARTICLE_WORDS_MIN = 500
TARGET_ARTICLE_WORDS_MAX = 1500

# --- Helper Functions ---

def _get_random_choice(options: List[Any], default: Any = None) -> Any:
    """Safely gets a random choice from a list.

    Args:
        options (List[Any]): The list of options to choose from.
        default (Any, optional): The value to return if the list is empty.
                                 Defaults to None.

    Returns:
        Any: A random element from the list, or the default value.
    """
    return random.choice(options) if options else default


def _generate_random_string_list(options: List[str], min_count: int, max_count: int) -> str:
    """Generates a comma-separated string from a random sample of options.

    Args:
        options (List[str]): List of possible string values.
        min_count (int): Minimum number of items to select.
        max_count (int): Maximum number of items to select.

    Returns:
        str: A comma-separated string of selected items, or an empty string.
    """
    if not options:
        return ""
    min_count = max(0, min_count)
    max_count = max(min_count, max_count)
    count = random.randint(min_count, max_count)
    count = min(count, len(options))
    selected = random.sample(options, count) if count > 0 else []
    return ", ".join(selected)


def random_date(start_str: str, end_str: str) -> datetime:
    """Generates a random timezone-aware datetime (UTC) between start and end dates.

    Args:
        start_str (str): Start date string in ISO 8601 format (e.g., "YYYY-MM-DDTHH:MM:SSZ").
        end_str (str): End date string in ISO 8601 format.

    Returns:
        datetime: A random datetime object with UTC timezone information.
                  Returns current UTC time if date parsing fails.
    """
    try:
        start_dt = datetime.fromisoformat(start_str)
        end_dt = datetime.fromisoformat(end_str)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)

        delta_seconds = int((end_dt - start_dt).total_seconds())
        random_seconds = random.randint(0, delta_seconds) if delta_seconds > 0 else 0
        return (start_dt + timedelta(seconds=random_seconds)).astimezone(timezone.utc)
    except ValueError as e:
        print(f"WARN: Invalid date format ('{start_str}', '{end_str}'). Using current time. Error: {e}")
        return datetime.now(timezone.utc)


# --- User Data Generation ---

def generate_user_basic(user_id_num: int, config: dict) -> Optional[Dict[str, Any]]:
    """Generates a dictionary representing a single user's basic attributes.

    Args:
        user_id_num (int): The numeric part of the user ID (e.g., 1 for user_001).
        config (dict): The application configuration dictionary.

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing user attributes,
                                  or None if config is invalid or generation fails.
    """
    try:
        data_cfg = config['data_generation']
        user_id = f"user_{user_id_num:03d}"

        experience_level = _get_random_choice(data_cfg['experience_levels'], 'Beginner')
        trading_goal = _generate_random_string_list(data_cfg['trading_goals_list'], 1, 2)
        account_age_months = random.randint(1, 36)
        trading_frequency = _get_random_choice(data_cfg['frequencies'], 'Medium')

        num_pref_assets = random.randint(1, 3)
        available_assets = data_cfg.get('preferred_assets_list', [])
        num_assets_to_sample = min(num_pref_assets, len(available_assets))
        preferred_asset_list = random.sample(
            available_assets, num_assets_to_sample
        ) if num_assets_to_sample > 0 else []
        preferred_assets = ", ".join(preferred_asset_list)

        fav_instrument_1 = None
        fav_instrument_2 = None
        if preferred_asset_list:
            fav_instrument_1 = random.choice(preferred_asset_list)
            fav_instrument_2_candidates = [a for a in preferred_asset_list if a != fav_instrument_1]
            if fav_instrument_2_candidates:
                fav_instrument_2 = random.choice(fav_instrument_2_candidates)

        fav_instrument_1_volume_perc = random.randint(40, 80) if fav_instrument_1 else 0
        fav_instrument_2_volume_perc = random.randint(10, 30) if fav_instrument_2 else 0

        avg_trade_duration_minutes = random.randint(15, 300)
        most_used_order_type = _get_random_choice(data_cfg['order_types'], 'Limit')
        win_rate_perc = round(random.uniform(40.0, 70.0), 2)
        average_leverage_multiple = round(random.uniform(1.0, 10.0), 1)

        user_attributes = {
            "user_id": user_id,
            "experience_level": experience_level,
            "trading_goal": trading_goal,
            "preferred_assets": preferred_assets,
            "account_age_months": account_age_months,
            "fav_instrument_1": fav_instrument_1,
            "fav_instrument_1_volume_perc": fav_instrument_1_volume_perc,
            "fav_instrument_2": fav_instrument_2,
            "fav_instrument_2_volume_perc": fav_instrument_2_volume_perc,
            "avg_trade_duration_minutes": avg_trade_duration_minutes,
            "most_used_order_type": most_used_order_type,
            "win_rate_perc": win_rate_perc,
            "average_leverage_multiple": average_leverage_multiple,
            "trading_frequency": trading_frequency,
            "profile_summary": None, # Populated later by AI
        }
        return user_attributes

    except KeyError as e:
        print(f"ERROR in generate_user_basic: Missing key in config['data_generation']: {e}")
        return None
    except Exception as e:
        user_id_str = f"user_{user_id_num:03d}" if 'user_id_num' in locals() else f"ID {user_id_num}"
        print(f"ERROR generating {user_id_str}: {e}")
        return None


# --- Media Data Generation ---

def _generate_media_metadata(
    media_id_num: int, item_type: str, config: dict
) -> Optional[Dict[str, Any]]:
    """Helper to generate common metadata for articles/videos.

    Args:
        media_id_num (int): Numeric part of the media ID.
        item_type (str): 'article' or 'video'.
        config (dict): Application configuration dictionary.

    Returns:
        Optional[Dict[str, Any]]: Dictionary of media metadata, or None on error.
    """
    try:
        data_cfg = config['data_generation']
        is_article = item_type == "article"
        prefix = "article" if is_article else "video"

        asset = _get_random_choice(data_cfg.get('preferred_assets_list'), 'ES')
        topic = _get_random_choice(data_cfg.get('media_tags'), 'General')
        activity = random.choice(['Futures', 'Options', 'Trading', 'Analysis'])
        title_templates = [
            f"Understanding {asset} {activity}", f"Mastering {topic} for {activity}",
            f"A Guide to {activity} with {asset}", f"Advanced {topic} Techniques"
        ]
        title = random.choice(title_templates)
        author_creator_value = _get_random_choice(data_cfg.get('creators_authors'), 'AutoGen')
        created_dt = random_date(data_cfg['start_date'], data_cfg['end_date'])
        created_iso_string = created_dt.isoformat()

        num_tags = random.randint(1, 3)
        available_tags = data_cfg.get('media_tags', [])
        num_tags_to_sample = min(num_tags, len(available_tags)) if available_tags else 0
        selected_tags = random.sample(available_tags, num_tags_to_sample) if num_tags_to_sample > 0 else []
        tags_string = ", ".join(selected_tags)

        content_len_value = None
        if is_article:
            content_len_value = random.randint(TARGET_ARTICLE_WORDS_MIN, TARGET_ARTICLE_WORDS_MAX)
        else: # video
            content_len_value = _get_random_choice(data_cfg.get('video_lengths_seconds'), 600)

        metadata = {
            "media_id": f"{prefix}_{media_id_num:03d}",
            "type": item_type,
            "title": title,
            "author_creator": author_creator_value,
            "created_date": created_iso_string, # Use ISO string for BQ TIMESTAMP
            "tags": tags_string,
            "main_text": None, # Populated later by AI
            "content_length": content_len_value, # Words for articles / seconds for videos
        }
        return metadata

    except KeyError as e:
        print(f"ERROR in _generate_media_metadata: Missing key in config: {e}")
        return None
    except Exception as e:
        id_prefix = "article" if 'item_type' in locals() and item_type == "article" else "video"
        media_id_str = f"{id_prefix}_{media_id_num:03d}" if 'media_id_num' in locals() else f"{item_type} ID {media_id_num}"
        print(f"ERROR generating {media_id_str} metadata: {e}")
        return None


def generate_article_metadata(article_id_num: int, config: dict) -> Optional[Dict[str, Any]]:
    """Generates article metadata ONLY.

    Args:
        article_id_num (int): Numeric part of the article ID.
        config (dict): Application configuration dictionary.

    Returns:
        Optional[Dict[str, Any]]: Dictionary of article metadata, or None on error.
    """
    return _generate_media_metadata(article_id_num, "article", config)


def generate_video_metadata(video_id_num: int, config: dict) -> Optional[Dict[str, Any]]:
    """Generates video metadata ONLY.

    Args:
        video_id_num (int): Numeric part of the video ID.
        config (dict): Application configuration dictionary.

    Returns:
        Optional[Dict[str, Any]]: Dictionary of video metadata, or None on error.
    """
    return _generate_media_metadata(video_id_num, "video", config)