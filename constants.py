# constants.py
# 시스템 프롬프트, 설정값 등 변하지 않는 값들 여기서 관리
OPENAI_MODEL    = "gpt-4o-mini"
CSS_FILE_PATH   = "\assets\styles.css"

# ============================
# MAP 사용 template
# ============================
# tool tip template
TOOLTIP_TEMPLATE = "{order}. {name}"

# popup template
POPUP_TEMPLATE = """
<div style='font-family: sans-serif;'>
    <b style='font-size: 14px;'>{order}.{name}</b><br>
    <hr style='margin: 5px 0;'>
</div>
"""

# icon template
MARKER_ICON_TEMPLATE = """
<div style="background:#4A90E2;color:white;border-radius:50%;width:28px;height:28px;line-height:28px;text-align:center;font-weight:bold">
    {order}
</div>
"""

PLACE_CATEGORY_MAP = {
    # --- 문화 및 역사 (STAY_TIME_CONFIG 기준) ---
    "art_gallery": ["art_gallery"],
    "art_museum": ["art_museum"],
    "museum": ["museum", "history_museum", "planetarium"],
    "castle": ["castle"],
    "cultural_landmark": ["cultural_landmark", "historical_landmark", "historical_place", "monument"],
    "historical_place": ["historical_place"],
    "history_museum": ["history_museum"],
    "monument": ["monument", "sculpture"],
    "sculpture": ["sculpture"],
    "cultural_center": ["cultural_center", "auditorium", "community_center", "convention_center", "art_studio"],

    # --- 엔터테인먼트 및 여가 ---
    "amusement_park": ["amusement_park", "amusement_center", "roller_coaster", "water_park"],
    "aquarium": ["aquarium"],
    "zoo": ["zoo", "wildlife_park", "wildlife_refuge"],
    "botanical_garden": ["botanical_garden"],
    "wildlife_park": ["wildlife_park"],
    "water_park": ["water_park"],
    "casino": ["casino"],
    "movie_theater": ["movie_theater", "movie_rental"],
    "performing_arts_theater": ["performing_arts_theater", "amphitheatre", "concert_hall", "philharmonic_hall"],
    "opera_house": ["opera_house"],

    # --- 공원 및 자연 ---
    "park": ["park", "city_park", "dog_park", "playground", "plaza"],
    "city_park": ["city_park"],
    "national_park": ["national_park", "state_park"],
    "hiking_area": ["hiking_area", "mountain_peak", "nature_preserve", "woods"],
    "garden": ["garden"],
    "beach": ["beach", "lake", "river", "island"],
    "marina": ["marina", "fishing_pier", "fishing_pond"],
    "picnic_ground": ["picnic_ground", "barbecue_area"],

    # --- 식음료 (모든 세부 음식점 포함) ---
    "restaurant": [
        "restaurant", "american_restaurant", "asian_restaurant", "chinese_restaurant", 
        "french_restaurant", "italian_restaurant", "japanese_restaurant", "korean_restaurant", 
        "mexican_restaurant", "thai_restaurant", "seafood_restaurant", "steak_house", 
        "sushi_restaurant", "vietnamese_restaurant", "fine_dining_restaurant", "food_court",
        "fast_food_restaurant", "pizza_restaurant", "hamburger_restaurant", "ramen_restaurant"
        # ... 기타 모든 *_restaurant 타입 포함
    ],
    "cafe": ["cafe", "cat_cafe", "dog_cafe", "internet_cafe"],
    "bar": ["bar", "pub", "wine_bar", "night_club", "cocktail_bar", "lounge_bar", "sports_bar"],
    "bakery": ["bakery", "cake_shop", "pastry_shop"],
    "coffee_shop": ["coffee_shop", "tea_house", "juice_shop", "coffee_roastery"],
    "ice_cream_shop": ["ice_cream_shop", "dessert_shop", "dessert_restaurant", "confectionery"],

    # --- 쇼핑 ---
    "shopping_mall": ["shopping_mall"],
    "department_store": ["department_store", "hypermarket", "warehouse_store"],
    "clothing_store": ["clothing_store", "shoe_store", "jewelry_store", "womens_clothing_store", "sportswear_store"],
    "market": ["market", "farmers_market", "flea_market", "grocery_store", "supermarket"],
    "gift_shop": ["gift_shop", "toy_store", "book_store"],
    "duty_free_store": ["duty_free_store"],

    # --- 종교 및 기타 ---
    "church": ["church", "mosque", "synagogue", "hindu_temple", "buddhist_temple", "shinto_shrine"],
    "hindu_temple": ["hindu_temple"],
    "mosque": ["mosque"],
    "synagogue": ["synagogue"],
    "shrine": ["shinto_shrine"],
    "library": ["library"],
    "university": ["university", "school", "secondary_school", "primary_school", "college"],
}

# 실내/실외를 위한 카테고리값.
INDOOR_TYPES = {
    # 문화 및 예술
    "art_gallery", "art_museum", "museum", "history_museum", "planetarium",
    "cultural_center", "auditorium", "community_center", "convention_center", "art_studio",
    "library", "library",

    # 엔터테인먼트 (실내형)
    "casino", "movie_theater", "movie_rental", "performing_arts_theater", 
    "concert_hall", "philharmonic_hall", "opera_house", "amusement_center",
    "aquarium", # 아쿠아리움은 대부분 실내이므로 추가

    # 식음료 (전체)
    "restaurant", "american_restaurant", "asian_restaurant", "chinese_restaurant", 
    "french_restaurant", "italian_restaurant", "japanese_restaurant", "korean_restaurant", 
    "mexican_restaurant", "thai_restaurant", "seafood_restaurant", "steak_house", 
    "sushi_restaurant", "vietnamese_restaurant", "fine_dining_restaurant", "food_court",
    "fast_food_restaurant", "pizza_restaurant", "hamburger_restaurant", "ramen_restaurant",
    "cafe", "cat_cafe", "dog_cafe", "internet_cafe",
    "bar", "pub", "wine_bar", "night_club", "cocktail_bar", "lounge_bar", "sports_bar",
    "bakery", "cake_shop", "pastry_shop",
    "coffee_shop", "tea_house", "juice_shop", "coffee_roastery",
    "ice_cream_shop", "dessert_shop", "dessert_restaurant", "confectionery",

    # 쇼핑 (전체)
    "shopping_mall", "department_store", "hypermarket", "warehouse_store",
    "clothing_store", "shoe_store", "jewelry_store", "womens_clothing_store", "sportswear_store",
    "grocery_store", "supermarket", "gift_shop", "toy_store", "book_store", "duty_free_store",

    # 종교 및 교육
    "church", "mosque", "synagogue", "hindu_temple", "buddhist_temple", "shinto_shrine",
    "university", "school", "secondary_school", "primary_school", "college",
}

