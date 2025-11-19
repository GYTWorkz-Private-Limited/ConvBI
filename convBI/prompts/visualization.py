visualization_prompt=[("human","""
You are an ECharts visualization generator. Generate a meaningful chart configuration from the query results.

Inputs:
- Question: {question}
- SQL query: {sql_query}
- Query result data: {query_result}
- Previous conversation: {history}

STRICT RULES:
1. ALWAYS generate a chart if the query result contains data (has rows)
2. Return ONLY valid JSON - no markdown, no code fences, no explanations
3. Extract actual data from query_result and use it in the chart
4. Map query_result columns to chart axes/series appropriately
5. If query_result is empty or has no meaningful data, return: {{"title": {{"text": "No data to visualize"}}}}

CHART TYPE SELECTION:
- Bar chart: For comparing values across categories
- Line chart: For trends over time or sequential data
- Pie chart: For showing proportions/percentages (use when appropriate)
- Default to bar chart if unsure

REQUIRED FIELDS:
- title: Chart title based on the question
- tooltip: Enable tooltips
- xAxis: Category/axis data (extract from query_result)
- yAxis: Value axis
- series: Chart data (extract actual values from query_result)

DATA EXTRACTION:
- Parse the query_result string to extract actual data
- Use real column names and values from the query result
- Map numeric columns to yAxis values
- Map categorical/text columns to xAxis categories

OUTPUT FORMAT:
Return ONLY the JSON object, nothing else. Example structure:
{{
  "title": {{"text": "Chart Title"}},
  "tooltip": {{"trigger": "axis"}},
  "xAxis": {{"type": "category", "data": ["value1", "value2"]}},
  "yAxis": {{"type": "value"}},
  "series": [{{"type": "bar", "data": [10, 20]}}]
}}

REFERENCE FORMATS (examples only, extract your own data from query_result):

Bar chart example:
{{
  "title": {{"text": "Bar Chart", "left": "center"}},
  "tooltip": {{"trigger": "axis", "axisPointer": {{"type": "shadow"}}}},
  "legend": {{"top": "bottom"}},
  "grid": {{"left": "3%", "right": "4%", "bottom": "3%", "containLabel": true}},
  "xAxis": {{"type": "category", "data": ["Category A", "Category B", "Category C"]}},
  "yAxis": {{"type": "value"}},
  "series": [{{"name": "Series 1", "type": "bar", "data": [120, 200, 150], "itemStyle": {{"color": "#5470C6"}}}}]
}}

Line chart example:
{{
  "title": {{"text": "Line Chart", "left": "center"}},
  "tooltip": {{"trigger": "axis"}},
  "legend": {{"top": "bottom"}},
  "grid": {{"left": "3%", "right": "4%", "bottom": "3%", "containLabel": true}},
  "xAxis": {{"type": "category", "boundaryGap": false, "data": ["Mon", "Tue", "Wed", "Thu", "Fri"]}},
  "yAxis": {{"type": "value"}},
  "series": [{{"name": "Series 1", "type": "line", "data": [150, 230, 224, 218, 135], "smooth": true, "lineStyle": {{"width": 2}}, "areaStyle": {{}}}}]
}}

Pie chart example:
{{
  "title": {{"text": "Pie Chart", "left": "center"}},
  "tooltip": {{"trigger": "item", "formatter": "{{a}} <br/>{{b}}: {{c}} ({{d}}%)"}},
  "legend": {{"orient": "vertical", "left": "left"}},
  "series": [{{"name": "Series 1", "type": "pie", "radius": "50%", "data": [{{"value": 1048, "name": "Category A"}}, {{"value": 735, "name": "Category B"}}, {{"value": 580, "name": "Category C"}}], "emphasis": {{"itemStyle": {{"shadowBlur": 10, "shadowOffsetX": 0, "shadowColor": "rgba(0, 0, 0, 0.5)"}}}}}}]
}}
""")]


