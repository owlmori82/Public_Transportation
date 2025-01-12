import streamlit as st
import geopandas as gpd
from shapely.geometry import LineString
import json
import numpy as np
import folium
from folium.features import GeoJsonTooltip
import random
from streamlit_folium import folium_static

@st.cache_data
def crime_worst_x(rank, item):
    merged_df = gpd.read_file("/media/mk/Data/Documents/source/public_traffic/data/2023_東京都犯罪件数.geojson")
    gdf = gpd.GeoDataFrame(merged_df, geometry='geometry')
    gdf = gdf.to_crs(epsg=4326)
    return gdf.sort_values(item, ascending=False).head(rank)

def root_map():
    gdf_railway = gpd.read_file("/media/mk/Data/Documents/source/public_traffic/data/N02-19_RailroadSection.geojson")
    in_tokyo = ['横須賀線', '山手線', '赤羽線（埼京線）', '総武線', '中央線', '東海道線', '東北線（埼京線）', '東北線', '南武線', '武蔵野線']
    return gdf_railway[(gdf_railway["運営会社"] == "東日本旅客鉄道") & (gdf_railway["路線名"].isin(in_tokyo))]

def draw_tokyo():
    tokyo23_location = [35.658593, 139.745441]
    tokyo_map = folium.Map(location=tokyo23_location, tiles='cartodbpositron', zoom_start=10)
    return tokyo_map

def draw_crime(gdf, t_map, item):
    geojson_data = json.loads(gdf.to_json())
    min_value = gdf[item].min()
    max_value = gdf[item].max()
    interval = max_value - min_value
    num_bins = 10 if interval >= 10 else interval
    threshold_scale = np.linspace(min_value, max_value, num_bins + 1, endpoint=True).tolist()
    choropleth = folium.Choropleth(
        geo_data=geojson_data,
        data=gdf,
        columns=['住所', item],
        key_on='properties.住所',
        fill_color='RdPu',
        threshold_scale=threshold_scale,
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name=item
    )
    choropleth.add_to(t_map)
    for feature in choropleth.geojson.data['features']:
        feature['properties']['tooltip'] = feature['properties']['住所'] + " / " + item + ":" + str(feature['properties'][item]) + "件"
    geojson = folium.GeoJson(
        choropleth.geojson.data,
        style_function=lambda feature: {
            'fillColor': feature['properties'].get('fillColor', 'gray'),
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.0
        },
        tooltip=GeoJsonTooltip(fields=['tooltip'], aliases=['住所:'], localize=True)
    )
    geojson.add_to(t_map)
    return t_map

def draw_lines(gdf_railway, map_object):
    def random_color():
        while True:
            color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
            if color not in ["#000000", "#FFFFFF", "#00000000"]:
                return color
    for line_name in gdf_railway["路線名"].unique():
        filtered_lines = gdf_railway[gdf_railway["路線名"] == line_name]["geometry"]
        line_color = random_color()
        for line in filtered_lines:
            if line.geom_type == 'LineString':
                folium.PolyLine(
                    locations=[(coord[1], coord[0]) for coord in line.coords],
                    weight=2,
                    color=line_color
                ).add_to(map_object)
    return map_object

st.title("東京都犯罪件数と鉄道路線マップ")
if "map" not in st.session_state:
    st.session_state.map = draw_tokyo()

with st.form(key='setting'):
    st.text("2023年の東京都の丁目毎の犯罪件数と路線との関係をしめす。")
    item = st.selectbox(
        '犯罪種類',
        ('総合計', '凶悪犯計', '強盗', 'その他1', '粗暴犯計', '凶器準備集合', '暴行', '傷害', '脅迫', '恐喝',
         '侵入窃盗計', '金庫破り', '学校荒し', '事務所荒し', '出店荒し', '空き巣', '忍込み', '居空き', 'その他2',
         '非侵入窃盗計', '自動車盗', 'オートバイ盗', '自転車盗', '車上ねらい', '自販機ねらい', '工事場ねらい', 'すり',
         'ひったくり', '置引き', '万引き', 'その他3', 'その他計', '詐欺', '占有離脱物横領', 'その他知能犯', '賭博', 'その他刑法犯')
    )
    rank = st.radio(
        'ワースト○位まで',
        (0, 20, 50, 100, 150)
    )
    ok_btn = st.form_submit_button('設定')

if ok_btn:
    gdf_crime = crime_worst_x(rank, item)
    gdf_railway = root_map()
    st.session_state.map = draw_tokyo()
    st.session_state.map = draw_crime(gdf_crime, st.session_state.map, item)
    st.session_state.map = draw_lines(gdf_railway, st.session_state.map)
     
map_data = folium_static(st.session_state.map,width=700)
