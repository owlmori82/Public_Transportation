import streamlit as st
import geopandas as gpd
from shapely.geometry import LineString
import json
import numpy as np
import folium
from folium.features import GeoJsonTooltip
import random
from streamlit_folium import folium_static
from PIL import Image

@st.cache_data
def crime_worst_x(rank, item,year):
    merged_df = gpd.read_file("./data/" + year + "_東京都犯罪件数.geojson")
    gdf = gpd.GeoDataFrame(merged_df, geometry='geometry')
    gdf = gdf.to_crs(epsg=4326)
    return gdf.sort_values(item, ascending=False).head(rank)

def root_map():
    gdf_railway = gpd.read_file("./data/N02-19_RailroadSection.geojson")
    in_tokyo = ['横須賀線', '山手線', '赤羽線（埼京線）', '総武線', '中央線', '東海道線', '東北線（埼京線）', '東北線', '南武線', '武蔵野線']
    return gdf_railway[(gdf_railway["運営会社"] == "東日本旅客鉄道") & (gdf_railway["路線名"].isin(in_tokyo))]

def draw_tokyo():
    tokyo23_location = [35.658593, 139.745441]
    tokyo_map = folium.Map(location=tokyo23_location, tiles='cartodbpositron', zoom_start=10)
    return tokyo_map

def draw_crime(gdf,t_map,item):
    t_gdf = gdf[gdf[item] > 0]
    #geojsonに変換
    geojson_data = json.loads(t_gdf.to_json())
    # 総合計の最小値と最大値を取得
    min_value = gdf[item].min()
    max_value = gdf[item].max()

    # しきい値のスケールを動的に設定 (例: 10区分)
    interval = max_value - min_value
    if  interval < 10:
        num_bins = interval
    else:
        num_bins = 10
    threshold_scale = np.linspace(min_value, max_value, num_bins + 1,endpoint=True).tolist()
    #スケールの幅が3個以下の場合、スケールの幅を広げる
    if len(threshold_scale) < 4:
        while (len(threshold_scale) < 4):
            threshold_scale.append(max(threshold_scale) + 1)
    print(min_value,max_value)
    print(threshold_scale)
       
    # Choroplethを描画して、色分けを適用
    choropleth = folium.Choropleth(
        geo_data= geojson_data,
        data=gdf,
        columns=['住所',item],
        key_on='properties.住所',
        fill_color='RdPu',
        threshold_scale=threshold_scale,
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name= item
    )
    choropleth.add_to(t_map)

    # Choroplethの GeoJson データにホバー用フィールドを追加
    for feature in choropleth.geojson.data['features']:
        feature['properties']['tooltip'] = feature['properties']['住所'] + " / " + item + ":" + str(feature['properties'][item]) + "件"

    # GeoJsonを再構成してホバーを追加
    geojson = folium.GeoJson(
        choropleth.geojson.data,
        style_function = lambda feature:{
            'fillColor':feature['properties'].get('fillColor','gray'),    # Choropleth の色を維持
            'color':'black',  #ポリゴンの枠線の色
            'weight':0.5,     #枠線の太さ
            'fillOpacity':0.0 #塗りつぶしの透明度
        },
        tooltip=GeoJsonTooltip(
            fields=['tooltip'],  # 追加した 'tooltip' フィールドを使用
            aliases=['住所:'],   # 表示する際のラベル
            localize=True        # ローカライズ
        )
    )

    geojson.add_to(t_map)   
    if max_value == 0:
        return 'NG'
    else:
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

st.markdown("""
2023年の東京都の犯罪件数を丁目区域毎に地図上に色分けして表示します。

1. **犯罪種類と表示件数の設定**  
   - 指定した犯罪種類と件数に基づき、該当地域を地図上で色分けして表示します。

2. **犯罪件数に応じた色分け表示**  
   - 地図上で犯罪件数に応じて地域を色分けし、一目で状況を把握できます。

3. **詳細情報のポップアップ表示**  
   - 色分けされた地域にカーソルを合わせると、該当地域の住所と犯罪件数がポップアップで表示されます。

4. **地図の縮尺変更**  
   - 地図は自由に拡大・縮小可能で、詳細確認や広域把握が可能です。

5. **JR路線図の重ね合わせ表示**  
   - 地図上にJR路線図を表示し、路線と犯罪多発地域の関係性を確認できます。          
"""
)
st.text("【表示例】")
img = Image.open("./data/show_map.png")
st.image(img)

if "map" not in st.session_state:
    st.session_state.map = draw_tokyo()

with st.form(key='setting'):
    
    t_year = st.selectbox(
        '対象年',
        ('2019','2020','2021','2022','2023')
    )
    item = st.selectbox(
        '犯罪種類',
        ('総合計', '凶悪犯計', '強盗', 'その他1', '粗暴犯計', '凶器準備集合', '暴行', '傷害', '脅迫', '恐喝',
         '侵入窃盗計', '金庫破り', '学校荒し', '事務所荒し', '出店荒し', '空き巣', '忍込み', '居空き', 'その他2',
         '非侵入窃盗計', '自動車盗', 'オートバイ盗', '自転車盗', '車上ねらい', '自販機ねらい', '工事場ねらい', 'すり',
         'ひったくり', '置引き', '万引き', 'その他3', 'その他計', '詐欺', '占有離脱物横領', 'その他知能犯', '賭博', 'その他刑法犯')
    )
    rank = st.radio(
        'ワースト○位まで表示',
        (10, 20, 50, 100, 150)
    )
   
    ok_btn = st.form_submit_button('設定')

if ok_btn:
    gdf_crime = crime_worst_x(rank, item,t_year)
    gdf_railway = root_map()
    st.session_state.map = draw_tokyo()
    st.session_state.map = draw_crime(gdf_crime, st.session_state.map, item)
    if st.session_state.map == 'NG':
        st.text("0件のため表示できるデータがありません")
        st.session_state.map = draw_tokyo()
    else:
        st.session_state.map = draw_lines(gdf_railway, st.session_state.map)
st.text("【設定条件で地図上に表示】")     
map_data = folium_static(st.session_state.map,width=700)
