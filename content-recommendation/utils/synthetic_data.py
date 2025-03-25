"""
Provides functions to generate synthetic data for users, articles, and videos
based on predefined lists of attributes and some simple logic.
"""
import random
from datetime import datetime, timedelta

def random_date(start_str, end_str):
    """Generate a random datetime between `start` and `end` strings."""
    start = datetime.fromisoformat(start_str)
    end = datetime.fromisoformat(end_str)
    return start + timedelta(
        seconds=random.randint(0, int((end - start).total_seconds()))
    )

def generate_article_text(title, tags, config):
    """Generate synthetic article text based on title and tags."""
    intro = f"This article discusses {title.lower()}, focusing on aspects relevant to futures trading. "
    body_parts = []
    if "Beginner" in tags:
        body_parts.append("We start with the basic concepts everyone should understand. ")
    if "Intermediate" in tags:
        body_parts.append("Building on the fundamentals, we delve into more complex strategies. ")
    if "Advanced" in tags:
        body_parts.append("This section covers advanced techniques and requires a solid understanding of the market. ")
    if "Risk Management" in tags:
        body_parts.append("A key part of successful trading is managing risk effectively. We explore various risk management tools. ")
    if "Technical Analysis" in tags:
        body_parts.append("Technical indicators like RSI, MACD, and Moving Averages are crucial for analyzing price action. ")
    if "Fundamental Analysis" in tags:
        body_parts.append("Understanding economic indicators and news releases is vital for fundamental analysis. ")
    if "Options" in tags:
        body_parts.append("We also touch upon how options can be used in conjunction with futures. ")
    if any(asset in tags or asset in title for asset in ["ES", "E-mini S&P 500"]):
        body_parts.append("The E-mini S&P 500 is a popular contract for many traders. ")
    if any(asset in tags or asset in title for asset in ["CL", "Crude Oil"]):
        body_parts.append("Crude Oil futures are known for their volatility and liquidity. ")
    if any(asset in tags or asset in title for asset in ["GC", "Gold"]):
        body_parts.append("Gold often acts as a safe-haven asset. ")

    num_paragraphs = random.randint(3, 6)
    # Ensure we don't try to sample more than available
    num_to_sample = min(num_paragraphs, len(body_parts))
    if num_to_sample > 0:
        body = " ".join(random.sample(body_parts, num_to_sample))
    else:
        body = "No specific content generated for the given tags."
    conclusion = "In conclusion, understanding these principles is essential for anyone looking to trade futures effectively."
    return intro + body + conclusion

def generate_video_transcript(title, tags, config):
    """Generate synthetic video transcript based on title and tags."""
    intro = f"Welcome to this video about {title.lower()}. Let's dive right in. "
    body_parts = []
    if "Beginner" in tags:
        body_parts.append("First, we'll cover the absolute basics. ")
    if "Intermediate" in tags:
        body_parts.append("Next, we'll move on to some intermediate level concepts. ")
    if "Advanced" in tags:
        body_parts.append("For advanced users, we have some high-level strategies to discuss. ")
    if "Risk Management" in tags:
        body_parts.append("Remember, always manage your risk. We'll show you how. ")
    if "Technical Analysis" in tags:
        body_parts.append("Let's look at some charts and apply technical indicators. ")
    if "Fundamental Analysis" in tags:
        body_parts.append("We'll also cover the fundamental factors impacting the market. ")
    if "Trading Psychology" in tags:
        body_parts.append("Don't underestimate the role of psychology in trading. ")

    num_sentences = random.randint(10, 25)
    # Decide how many body parts to sample, ensuring it's between 1 and len(body_parts) if possible
    if len(body_parts) > 0:
        num_to_sample = random.randint(1, len(body_parts))
        sampled_body = random.sample(body_parts, num_to_sample)
        body = " ".join(sampled_body * 3) # Duplicate for length
    else:
        body = "No specific content generated for the given tags."
    conclusion = f"So that's a brief overview of {title.lower()}. Thanks for watching!"
    return intro + body[:int(len(body)*0.8) if len(body) > 0 else 0] + conclusion

def generate_user(user_id_num, config):
    """Generates synthetic data for a single user."""
    data_gen_config = config['data_generation']
    experience = random.choice(data_gen_config['experience_levels'])
    goals = random.sample(data_gen_config['trading_goals_list'], random.randint(1, 2))
    assets = random.sample(data_gen_config['preferred_assets_list'], random.randint(1, 3))
    account_age = random.randint(1, 36)
    fav_asset_1 = random.choice(assets) if assets else random.choice(data_gen_config['preferred_assets_list'])
    fav_asset_2 = random.choice([a for a in assets if a != fav_asset_1]) if len(assets) > 1 else (
        random.choice(data_gen_config['preferred_assets_list']) if random.random() > 0.5 else None)

    return {
        "user_id": f"user_{user_id_num:03d}",
        "experience_level": experience,
        "trading_goal": ", ".join(goals),
        "preferred_assets": ", ".join(assets),
        "account_age_months": account_age,
        "fav_instrument_1": fav_asset_1,
        "fav_instrument_1_volume_perc": random.randint(40, 80) if fav_asset_1 else 0,
        "fav_instrument_2": fav_asset_2,
        "fav_instrument_2_volume_perc": random.randint(10, 30) if fav_asset_2 else 0,
        "avg_trade_duration_minutes": random.randint(15, 300),
        "most_used_order_type": random.choice(data_gen_config['order_types']),
        "win_rate_perc": round(random.uniform(40, 70), 2),
        "average_leverage_multiple": round(random.uniform(1, 10), 1),
        "trading_frequency": random.choice(data_gen_config['frequencies'])
    }

def generate_article(article_id_num, config):
    """Generates synthetic data for a single article."""
    data_gen_config = config['data_generation']
    title_options = [
        f"Understanding {random.choice(data_gen_config['preferred_assets_list'])} Futures",
        f"Mastering {random.choice(['Risk Management', 'Technical Analysis'])} in Trading",
        f"A Beginner's Guide to {random.choice(['Futures', 'Options'])}",
        f"Advanced Strategies for Trading {random.choice(data_gen_config['preferred_assets_list'])}",
        f"The Impact of {random.choice(['Economic News', 'Market Sentiment'])} on {random.choice(data_gen_config['preferred_assets_list'])}",
        f"Using {random.choice(['Volume Profile', 'Order Flow'])} for Better Entries",
        f"Trading Psychology: Overcoming {random.choice(['Fear', 'Greed'])}",
        f"Developing a Profitable Trading Plan"
    ]
    title = random.choice(title_options)
    author = random.choice(data_gen_config['creators_authors'])
    created = random_date(data_gen_config['start_date'], data_gen_config['end_date']).isoformat() + "Z"
    tags = random.sample(data_gen_config['media_tags'], random.randint(2, 4))
    content = generate_article_text(title, tags, config)
    return {
        "media_id": f"article_{article_id_num:03d}",
        "type": "article",
        "title": title,
        "author": author,
        "created_date": created,
        "tags": tags,
        "content": content,
        "content_length_words": len(content.split())
    }

def generate_video(video_id_num, config):
    """Generates synthetic data for a single video."""
    data_gen_config = config['data_generation']
    title_options = [
        f"Video Tutorial: Trading {random.choice(data_gen_config['preferred_assets_list'])}",
        f"Learn {random.choice(['Order Types', 'Chart Patterns'])}",
        f"Market Analysis: {random.choice(data_gen_config['preferred_assets_list'])} Outlook",
        f"Trading Strategy Breakdown: {random.choice(['Scalping', 'Day Trading', 'Swing Trading'])}",
        f"Risk Management Techniques for Futures Traders",
        f"Understanding {random.choice(['Open Interest', 'Implied Volatility'])}",
        f"Live Trading Session Recap",
        f"Expert Interview: The Future of {random.choice(data_gen_config['preferred_assets_list'])}"
    ]
    title = random.choice(title_options)
    creator = random.choice(data_gen_config['creators_authors'])
    created = random_date(data_gen_config['start_date'], data_gen_config['end_date']).isoformat() + "Z"
    tags = random.sample(data_gen_config['media_tags'], random.randint(2, 4))
    transcript = generate_video_transcript(title, tags, config)
    length = random.choice(data_gen_config['video_lengths_seconds'])
    return {
        "media_id": f"video_{video_id_num:03d}",
        "type": "video",
        "title": title,
        "creator": creator,
        "created_date": created,
        "tags": tags,
        "transcript": transcript,
        "video_length_seconds": length,
        "transcript_length_words": len(transcript.split())
    }