import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
import re
import streamlit.components.v1 as components
import json
import plotly.express as px

# Setup page configuration
st.set_page_config(page_title="Quran Analytics Dashboard", layout="wide", page_icon="📖")

# --- Custom CSS Styling ---
st.markdown("""
<style>
    /* Enhanced Metric Container */
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 5% 5% 5% 10%;
        border-radius: 10px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.05);
        transition: transform 0.2s ease-in-out;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 4px 4px 12px rgba(0,0,0,0.1);
    }
    /* Dark Theme considerations */
    @media (prefers-color-scheme: dark) {
        div[data-testid="metric-container"] {
            background-color: #1e1e2e;
            border-color: #2d2d3b;
        }
    }
    
    /* Typography tweaks */
    h1 {
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #1f77b4, #2ca02c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    h2, h3 {
        font-weight: 600;
        color: #1f77b4;
    }
    @media (prefers-color-scheme: dark) {
        h1 {
            background: -webkit-linear-gradient(45deg, #4da6ff, #5cd65c);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        h2, h3 {
            color: #4da6ff;
        }
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_quran_data():
    """
    Fetches the full Uthmani Quran JSON from api.alquran.cloud.
    It parses the Surah and Ayah details, strips Arabic diacritics for accurate
    word counting, and computes aggregations.
    """
    url = "https://api.alquran.cloud/v1/quran/quran-uthmani"
    response = requests.get(url)
    if response.status_code != 200:
        st.error("Error fetching data from API")
        return pd.DataFrame()
    
    data = response.json().get("data", {}).get("surahs", [])
    
    # Process data
    surah_list = []
    
    # Regex matching common Arabic diacritics (Tashkeel) including Waqf marks
    arabic_diacritics = re.compile(
        "[\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED]"
    )
    
    for surah in data:
        surah_id = surah.get("number")
        name = surah.get("englishName")
        arabic_name = surah.get("name")
        translation = surah.get("englishNameTranslation")
        revelation_type = surah.get("revelationType")
        ayahs = surah.get("ayahs", [])
        
        num_ayahs = len(ayahs)
        total_words = 0
        total_letters = 0
        
        for ayah in ayahs:
            text = ayah.get("text", "")
            # Remove diacritics
            clean_text = re.sub(arabic_diacritics, "", text)
            # Tokenize by whitespace
            words = [w for w in clean_text.split() if w.strip()]
            letters = clean_text.replace(" ", "")
            
            total_words += len(words)
            total_letters += len(letters)
            
        surah_list.append({
            "Surah Number": surah_id,
            "Name": name,
            "Arabic Name": arabic_name,
            "Translation": translation,
            "Revelation Type": revelation_type,
            "Ayat Count": num_ayahs,
            "Word Count": total_words,
            "Letter Count": total_letters,
            "Average Words per Ayah": round(total_words / num_ayahs, 2) if num_ayahs > 0 else 0,
            "Average Letters per Word": round(total_letters / total_words, 2) if total_words > 0 else 0
        })
        
    df = pd.DataFrame(surah_list)
    
    # Calculate Percentage Shares globally (before filtering)
    total_quran_words = df["Word Count"].sum()
    total_quran_ayat = df["Ayat Count"].sum()
    total_quran_letters = df["Letter Count"].sum()
    
    df["Word Share (%)"] = (df["Word Count"] / total_quran_words) * 100
    df["Ayat Share (%)"] = (df["Ayat Count"] / total_quran_ayat) * 100
    df["Letter Share (%)"] = (df["Letter Count"] / total_quran_letters) * 100
    
    return df

# Title and initialization
st.title("📖 Quran Analytics Dashboard")
st.markdown("Explore and compare Surahs based on structural statistics using Python, Plotly, Matplotlib, and D3.js.")

with st.spinner("Fetching and processing vectorized Quran data..."):
    df_full = load_quran_data()

if df_full.empty:
    st.stop()

# --- Sidebar Filters ---
st.sidebar.header("🔍 Filter Criteria")

# Search functionality
search_query = st.sidebar.text_input("Search by Surah Name (English/Arabic/Translation)", "")

# 1. Filter by Revelation Type
rev_types = df_full["Revelation Type"].unique()
selected_rev_type = st.sidebar.multiselect("Select Revelation Type", rev_types, default=rev_types)

# 2. Filter by Surah Name
# First filter by Rev type and search query
filtered_by_rev = df_full[df_full["Revelation Type"].isin(selected_rev_type)]
if search_query:
    filtered_by_rev = filtered_by_rev[
        filtered_by_rev["Name"].str.contains(search_query, case=False, na=False) |
        filtered_by_rev["Arabic Name"].str.contains(search_query, case=False, na=False) |
        filtered_by_rev["Translation"].str.contains(search_query, case=False, na=False)
    ]

all_surahs_filtered = filtered_by_rev["Name"].tolist()
selected_surahs = st.sidebar.multiselect("Select Surah(s)", all_surahs_filtered, default=all_surahs_filtered)

# Apply final selection
filtered_df = filtered_by_rev[filtered_by_rev["Name"].isin(selected_surahs)]

if filtered_df.empty:
    st.warning("No Surahs selected. Please adjust your filters.")
    st.stop()

# --- Setup Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 Visualizations", "🔍 Surah Details", "🗄️ Raw Data"])

with tab1:
    # --- KPI Section ---
    st.subheader("Key Statistics (Filtered Selection)")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Surahs", len(filtered_df))
    with col2:
        st.metric("Total Ayat", f"{filtered_df['Ayat Count'].sum():,}")
    with col3:
        st.metric("Total Words", f"{filtered_df['Word Count'].sum():,}")
    with col4:
        st.metric("Total Letters", f"{filtered_df['Letter Count'].sum():,}")
    with col5:
        avg_words = round(filtered_df['Word Count'].sum() / filtered_df['Ayat Count'].sum(), 2) if filtered_df['Ayat Count'].sum() > 0 else 0
        st.metric("Avg Words/Ayah", f"{avg_words}")

    st.divider()

    # --- Comparison View ---
    st.subheader("Surah Comparison Data")
    st.dataframe(
        filtered_df[["Surah Number", "Name", "Arabic Name", "Revelation Type", "Ayat Count", "Word Count", "Letter Count", "Word Share (%)", "Ayat Share (%)"]].sort_values("Surah Number").set_index("Surah Number").style.format({
            "Word Share (%)": "{:.2f}%", 
            "Ayat Share (%)": "{:.2f}%",
            "Ayat Count": "{:,}",
            "Word Count": "{:,}",
            "Letter Count": "{:,}"
        }).background_gradient(subset=['Word Count', 'Ayat Count'], cmap='Blues'), 
        use_container_width=True,
        height=350
    )


with tab2:
    # --- Plotly Visualizations ---
    st.subheader("Interactive Share Breakdown")
    st.markdown("Explore the proportional share of the Quran using dynamic, clickable charts. Click on Sunburst segments to zoom in!")

    control_col1, control_col2 = st.columns(2)
    with control_col1:
        pie_metric = st.selectbox("Select Metric for Breakdown:", ["Ayat Count", "Word Count", "Letter Count"])
    with control_col2:
        chart_type = st.radio("Select Chart Type:", ["Sunburst (Hierarchical)", "Donut Chart"], horizontal=True)

    if chart_type == "Donut Chart":
        fig_pie = px.pie(
            filtered_df, 
            names="Name", 
            values=pie_metric, 
            title=f"{pie_metric} Share by Surah",
            hole=0.4,
            hover_data=[f"{pie_metric.split()[0]} Share (%)", "Revelation Type"]
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        # Hide legend to avoid clutter when many surahs are selected
        fig_pie.update_layout(showlegend=False, margin=dict(t=40, l=0, r=0, b=0))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        fig_sun = px.sunburst(
            filtered_df,
            path=["Revelation Type", "Name"], 
            values=pie_metric, 
            title=f"{pie_metric} Share Hierarchical View",
            color="Revelation Type",
            color_discrete_map={"Meccan": "#1f77b4", "Medinan": "#ff7f0e", "(?)": "#cccccc"}
        )
        fig_sun.update_traces(textinfo="label+percent parent")
        fig_sun.update_layout(margin=dict(t=40, l=0, r=0, b=0))
        st.plotly_chart(fig_sun, use_container_width=True)

    st.divider()

    st.subheader("Statistical Distributions")
    scat_col1, scat_col2 = st.columns(2)
    
    with scat_col1:
        st.markdown("**Interactive Scatter: Ayat vs. Word Density**")
        # Replace the static matplotlib scatter with an interactive Plotly scatter
        fig_scatter = px.scatter(
            filtered_df,
            x="Ayat Count",
            y="Word Count",
            color="Revelation Type",
            size="Letter Count",
            hover_name="Name",
            hover_data=["Revelation Type", "Average Words per Ayah"],
            color_discrete_map={"Meccan": "#1f77b4", "Medinan": "#ff7f0e"},
            title="Density Analysis (Bubble Size = Letter Count)"
        )
        # Enable zoom, hover info makes this far superior to matplotlib
        st.plotly_chart(fig_scatter, use_container_width=True)
        
    with scat_col2:
        st.markdown("**Top 10 Longest Surahs by Word Count**")
        top_10_words = filtered_df.nlargest(10, 'Word Count').sort_values('Word Count', ascending=True)
        
        fig_bar = px.bar(
            top_10_words, 
            x="Word Count", 
            y="Name", 
            orientation='h',
            color="Revelation Type",
            color_discrete_map={"Meccan": "#1f77b4", "Medinan": "#ff7f0e"},
            text_auto='.2s',
            title="Highest Word Volumes"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # --- D3.js Visualization ---
    st.subheader("Interactive Word Volume Breakdown (D3.js)")
    st.markdown("Visualizing the internal **Share of Quran** (by word count). Tooltips represent the raw volume.")

    bubble_data = [{"id": row["Name"], "value": int(row["Word Count"]), "group": row["Revelation Type"]} for _, row in filtered_df.iterrows()]
    bubble_data_json = json.dumps(bubble_data)

    d3_html_code = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>D3 Bubble Chart</title>
        <script src="https://d3js.org/d3.v7.min.js"></script>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                display: flex;
                justify-content: center;
                background-color: transparent;
            }}
            .node {{
                stroke: #fff;
                stroke-width: 1.5px;
                cursor: pointer;
                transition: opacity 0.2s;
            }}
            .node:hover {{
                opacity: 0.8;
                filter: brightness(1.2);
            }}
            text {{
                font-size: 11px;
                pointer-events: none;
                text-anchor: middle;
                fill: #fff;
                font-weight: 600;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
            }}
            .tooltip {{
                position: absolute;
                text-align: center;
                padding: 10px;
                font-size: 13px;
                background: rgba(20, 20, 20, 0.95);
                color: #fff;
                border-radius: 6px;
                border: 1px solid rgba(255,255,255,0.2);
                pointer-events: none;
                opacity: 0;
                transition: opacity 0.2s, transform 0.1s;
                transform: translate(-50%, -100%);
                box-shadow: 0px 8px 16px rgba(0,0,0,0.2);
                z-index: 10;
            }}
        </style>
    </head>
    <body>
        <div id="chart"></div>
        <div id="tooltip" class="tooltip"></div>

        <script>
            const data = {bubble_data_json};

            const width = 800;
            const height = 600;

            const color = d3.scaleOrdinal()
                .domain(["Meccan", "Medinan"])
                .range(["#1f77b4", "#f79e25"]);

            const pack = d3.pack()
                .size([width - 10, height - 10])
                .padding(4);

            const root = d3.hierarchy({{children: data}})
                .sum(d => d.value)
                .sort((a, b) => b.value - a.value);

            const nodes = pack(root).leaves();

            const svg = d3.select("#chart").append("svg")
                .attr("width", width)
                .attr("height", height)
                .attr("viewBox", [0, 0, width, height])
                .attr("style", "max-width: 100%; height: auto;");
                
            const tooltip = d3.select("#tooltip");

            const node = svg.selectAll("g")
                .data(nodes)
                .join("g")
                .attr("transform", d => `translate(${{d.x}},${{d.y}})`);

            node.append("circle")
                .attr("r", d => d.r)
                .attr("fill", d => color(d.data.group))
                .attr("class", "node")
                .on("mouseover", function(event, d) {{
                    d3.select(this).attr("stroke", "#333").attr("stroke-width", 2);
                    tooltip.style("opacity", 1)
                           .html(`<strong>${{d.data.id}}</strong><hr style="margin:4px 0; border-color: rgba(255,255,255,0.2)">Words: ${{d.data.value}}<br>Type: ${{d.data.group}}`)
                           .style("left", event.pageX + "px")
                           .style("top", (event.pageY - 10) + "px");
                }})
                .on("mousemove", function(event) {{
                    tooltip.style("left", event.pageX + "px")
                           .style("top", (event.pageY - 10) + "px");
                }})
                .on("mouseout", function() {{
                    d3.select(this).attr("stroke", "#fff").attr("stroke-width", 1.5);
                    tooltip.style("opacity", 0);
                }});

            node.append("text")
                .attr("clip-path", d => `circle(${{d.r}})`)
                .selectAll("tspan")
                .data(d => d.data.id.split(/(?=[A-Z][^A-Z])/g))
                .join("tspan")
                .attr("x", 0)
                .attr("y", (d, i, nodes) => `${{i - nodes.length / 2 + 0.8}}em`)
                .text(d => {{
                    return d3.select(this.parentNode).datum().r > 20 ? d : "";
                }});
                
        </script>
    </body>
    </html>
    """
    components.html(d3_html_code, height=650)


with tab3:
    st.subheader("Deep Dive: Surah Specifics")
    
    selected_detail_surah = st.selectbox("Select a Surah for detailed analysis", filtered_df["Name"])
    
    if selected_detail_surah:
        surah_record = filtered_df[filtered_df["Name"] == selected_detail_surah].iloc[0]
        
        st.markdown(f"### Surah {surah_record['Name']} ({surah_record['Arabic Name']})")
        st.markdown(f"**English Translation:** {surah_record['Translation']}")
        st.markdown(f"**Revelation Location:** {surah_record['Revelation Type']}")
        
        detail_cols = st.columns(4)
        with detail_cols[0]:
            st.metric("Total Ayat", f"{surah_record['Ayat Count']:,}")
        with detail_cols[1]:
            st.metric("Total Words", f"{surah_record['Word Count']:,}")
        with detail_cols[2]:
            st.metric("Total Letters", f"{surah_record['Letter Count']:,}")
        with detail_cols[3]:
            # Provide context against the global quran average
            global_avg_words = round(df_full["Word Count"].mean(), 1)
            delta = round((surah_record['Word Count'] - global_avg_words) / global_avg_words * 100, 1) if global_avg_words > 0 else 0
            st.metric("vs Quran Avg Word Size", f"{surah_record['Word Count']:,}", f"{delta}%", delta_color="normal")
            
        st.divider()
        st.markdown("#### Density Metrics")
        dens_col1, dens_col2 = st.columns(2)
        with dens_col1:
            st.metric("Avg Words per Ayah", surah_record['Average Words per Ayah'])
        with dens_col2:
            st.metric("Avg Letters per Word", surah_record['Average Letters per Word'])
            
        st.divider()
        st.markdown("#### Volume as Percentage of Entire Quran")
        
        # Display progress bars
        st.caption(f"Ayat Share: **{surah_record['Ayat Share (%)']:.2f}%**")
        st.progress(min(surah_record['Ayat Share (%)'] / 100.0, 1.0))
        
        st.caption(f"Word Share: **{surah_record['Word Share (%)']:.2f}%**")
        st.progress(min(surah_record['Word Share (%)'] / 100.0, 1.0))
        
        st.caption(f"Letter Share: **{surah_record['Letter Share (%)']:.2f}%**")
        st.progress(min(surah_record['Letter Share (%)'] / 100.0, 1.0))


with tab4:
    st.subheader("Raw Data Export")
    st.markdown("View or download the parsed internal dataset.")
    
    st.dataframe(filtered_df, use_container_width=True)
    
    # Download Button
    @st.cache_data
    def convert_df(df):
        return df.to_csv(index=False).encode('utf-8')
    
    csv = convert_df(filtered_df)
    
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name='quran_analytics_data.csv',
        mime='text/csv',
    )
