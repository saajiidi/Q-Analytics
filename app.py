import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
import re
import streamlit.components.v1 as components
import json

# Setup page configuration
st.set_page_config(page_title="Quran Analytics Dashboard", layout="wide", page_icon="📖")

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
    # We strip these so our whitespace split isn't evaluating diacritic-only tokens.
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
        
        for ayah in ayahs:
            text = ayah.get("text", "")
            # Remove diacritics
            clean_text = re.sub(arabic_diacritics, "", text)
            # Tokenize by whitespace
            words = [w for w in clean_text.split() if w.strip()]
            
            # The Bismillah is generally included in Ayah 1 of most Surahs in this API.
            # No special distinction is applied, words are counted together.
            total_words += len(words)
            
        surah_list.append({
            "Surah Number": surah_id,
            "Name": name,
            "Arabic Name": arabic_name,
            "Translation": translation,
            "Revelation Type": revelation_type,
            "Ayat Count": num_ayahs,
            "Word Count": total_words
        })
        
    df = pd.DataFrame(surah_list)
    
    # Calculate Percentage Shares globally (before filtering)
    total_quran_words = df["Word Count"].sum()
    total_quran_ayat = df["Ayat Count"].sum()
    
    df["Word Share (%)"] = (df["Word Count"] / total_quran_words) * 100
    df["Ayat Share (%)"] = (df["Ayat Count"] / total_quran_ayat) * 100
    
    return df

# Title and initialization
st.title("📖 Quran Analytics Dashboard")
st.markdown("Explore and compare Surahs based on structural statistics using Python and D3.js.")

with st.spinner("Fetching and processing vectorized Quran data..."):
    df_full = load_quran_data()

if df_full.empty:
    st.stop()

# --- Sidebar Filters ---
st.sidebar.header("Filter Criteria")

# 1. Filter by Revelation Type
rev_types = df_full["Revelation Type"].unique()
selected_rev_type = st.sidebar.multiselect("Select Revelation Type", rev_types, default=rev_types)

# Use revelation type filter to scope available Surahs
filtered_by_rev = df_full[df_full["Revelation Type"].isin(selected_rev_type)]

# 2. Filter by Surah Name
all_surahs_filtered = filtered_by_rev["Name"].tolist()
selected_surahs = st.sidebar.multiselect("Select Surah(s)", all_surahs_filtered, default=all_surahs_filtered)

# Apply final selection
filtered_df = filtered_by_rev[filtered_by_rev["Name"].isin(selected_surahs)]

if filtered_df.empty:
    st.warning("No Surahs selected. Please adjust your filters.")
    st.stop()

# --- KPI Section ---
st.subheader("Key Statistics (Filtered Selection)")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Surahs", len(filtered_df))
with col2:
    st.metric("Total Ayat", f"{filtered_df['Ayat Count'].sum():,}")
with col3:
    st.metric("Total Words", f"{filtered_df['Word Count'].sum():,}")

st.divider()

# --- Comparison View ---
st.subheader("Surah Comparison Data")
st.dataframe(
    # Format percentages for table
    filtered_df.sort_values("Surah Number").set_index("Surah Number").style.format({
        "Word Share (%)": "{:.2f}%", 
        "Ayat Share (%)": "{:.2f}%",
        "Ayat Count": "{:,}",
        "Word Count": "{:,}"
    }), 
    use_container_width=True,
    height=250
)

st.divider()

# --- Matplotlib Visualizations ---
st.subheader("Statistical Distributions")

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("#### Top 10 Longest Surahs by Ayat Count")
    st.caption("Includes only the selected Surahs from the filters.")
    
    # Take top 10 from filtered
    top_10_ayat = filtered_df.nlargest(10, 'Ayat Count').sort_values('Ayat Count', ascending=True)
    
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.barh(top_10_ayat["Name"], top_10_ayat["Ayat Count"], color='#2CA02C')
    ax.set_xlabel('Total Ayat')
    ax.set_ylabel('Surah Name')
    ax.grid(axis='x', linestyle='--', alpha=0.6)
    plt.tight_layout()
    st.pyplot(fig)

with col_b:
    st.markdown("#### Ayat Count vs. Word Count Density")
    st.caption("Comparing sequence lengths across Meccan and Medinan Surahs.")
    
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    
    meccan = filtered_df[filtered_df["Revelation Type"] == "Meccan"]
    medinan = filtered_df[filtered_df["Revelation Type"] == "Medinan"]
    
    if not meccan.empty:
        ax2.scatter(meccan["Ayat Count"], meccan["Word Count"], alpha=0.7, label="Meccan", color="#1f77b4", edgecolors="k")
    if not medinan.empty:
        ax2.scatter(medinan["Ayat Count"], medinan["Word Count"], alpha=0.7, label="Medinan", color="#ff7f0e", edgecolors="k")
    
    ax2.set_xlabel("Ayat Count")
    ax2.set_ylabel("Word Count")
    ax2.grid(linestyle='--', alpha=0.6)
    if not (meccan.empty and medinan.empty):
        ax2.legend()
    plt.tight_layout()
    st.pyplot(fig2)

st.divider()

# --- D3.js Visualization ---
st.subheader("Interactive Word Volume Breakdown")
st.markdown("Visualizing the internal **Share of Quran** (by word count). Tooltips represent the raw volume.")

# Data Preparation for D3.js 
# We build a JSON string mapped with id, value, and group.
bubble_data = [{"id": row["Name"], "value": int(row["Word Count"]), "group": row["Revelation Type"]} for _, row in filtered_df.iterrows()]
bubble_data_json = json.dumps(bubble_data)

# Embedding D3 code into Streamlit
# We use st.components.v1.html() which acts as an isolated iframe. 
# We pass Python `bubble_data_json` string formatting inside the JavaScript block.
d3_html_code = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>D3 Bubble Chart</title>
    <!-- Load D3.js library linearly from CDN -->
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            display: flex;
            justify-content: center;
        }}
        .node {{
            stroke: #fff;
            stroke-width: 1.5px;
            cursor: pointer;
            transition: opacity 0.2s;
        }}
        .node:hover {{
            opacity: 0.8;
        }}
        text {{
            font-size: 11px;
            pointer-events: none;
            text-anchor: middle;
            fill: #fff;
            font-weight: 500;
        }}
        .tooltip {{
            position: absolute;
            text-align: center;
            padding: 8px;
            font-size: 13px;
            background: rgba(30, 30, 30, 0.9);
            color: #fff;
            border-radius: 6px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
            z-index: 10;
        }}
    </style>
</head>
<body>
    <div id="chart"></div>
    <div id="tooltip" class="tooltip"></div>

    <script>
        // Parse the embedded python JSON object 
        const data = {bubble_data_json};

        const width = 800;
        const height = 600;

        // D3 color scaling dynamically targeting categorical group mapped
        const color = d3.scaleOrdinal()
            .domain(["Meccan", "Medinan"])
            .range(["#1f77b4", "#ff7f0e"]);

        // Generates the hierarchical tree/bubble packaging
        const pack = d3.pack()
            .size([width - 10, height - 10])
            .padding(3);

        const root = d3.hierarchy({{children: data}})
            .sum(d => d.value)
            .sort((a, b) => b.value - a.value);

        const nodes = pack(root).leaves();

        // Render Canvas Base
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

        // Attach elements to Canvas elements and build interactive tooltip
        node.append("circle")
            .attr("r", d => d.r)
            .attr("fill", d => color(d.data.group))
            .attr("class", "node")
            .on("mouseover", function(event, d) {{
                d3.select(this).attr("stroke", "#333").attr("stroke-width", 2);
                tooltip.style("opacity", 1)
                       .html(`<strong>${{d.data.id}}</strong><br>Words: ${{d.data.value}}<br>Type: ${{d.data.group}}`)
                       .style("left", (event.pageX + 10) + "px")
                       .style("top", (event.pageY - 28) + "px");
            }})
            .on("mouseout", function() {{
                d3.select(this).attr("stroke", "#fff").attr("stroke-width", 1.5);
                tooltip.style("opacity", 0);
            }});

        // Text generation truncating sizes so it fits inside radius
        node.append("text")
            .attr("clip-path", d => `circle(${{d.r}})`)
            .selectAll("tspan")
            .data(d => d.data.id.split(/(?=[A-Z][^A-Z])/g))
            .join("tspan")
            .attr("x", 0)
            .attr("y", (d, i, nodes) => `${{i - nodes.length / 2 + 0.8}}em`)
            .text(d => {{
                // Only render text inside large bubbles to keep it clean
                return d3.select(this.parentNode).datum().r > 20 ? d : "";
            }});
            
    </script>
</body>
</html>
"""

# Embed HTML block to Native Streamlit
components.html(d3_html_code, height=650)
