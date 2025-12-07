#!/usr/bin/env python3
"""
YTM Dashboard Generator
Generates static HTML visualization of yield-to-maturity data
"""

import json
import sys
import os
from datetime import datetime
from typing import List, Dict

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager

# Provider color scheme
PROVIDER_COLORS = {
    'carmignac': '#FF6B6B',    # Coral red
    'sycomore': '#4ECDC4',     # Teal
    'rothschild': '#45B7D1'    # Sky blue
}

OUTPUT_PATH = 'dashboard.html'


def get_ytm_data() -> List[Dict]:
    """Query database for latest YTM records"""
    try:
        # Use absolute path
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'ytm_data.db')
        db = DatabaseManager(db_path)
        records = db.get_latest_records()

        if not records:
            print("⚠️  Warning: No data found in database")
            return []

        print(f"✅ Loaded {len(records)} fund records")
        return records

    except Exception as e:
        print(f"❌ Error querying database: {e}")
        sys.exit(1)


def transform_for_chart(records: List[Dict]) -> Dict:
    """Transform database records to Plotly JSON format"""
    if not records:
        return {'x': [], 'y': [], 'text': [], 'colors': [], 'customdata': []}

    return {
        'x': [r['fund_maturity'] for r in records],
        'y': [r['yield_to_maturity'] for r in records],
        'text': [r['fund_name'] for r in records],
        'colors': [PROVIDER_COLORS.get(r['provider'], '#999999') for r in records],
        'providers': [r['provider'] for r in records],
        'isins': [r['isin_code'] for r in records]
    }


def format_date(date_str: str) -> str:
    """Convert '2025-12-01' to 'December 2025'"""
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%B %Y')
    except:
        return date_str


def generate_table_html(records: List[Dict]) -> str:
    """Generate HTML table rows with provider color badges"""
    if not records:
        return '<tr><td colspan="6">No data available</td></tr>'

    rows = []
    for record in records:
        provider = record.get('provider', 'unknown')
        color = PROVIDER_COLORS.get(provider, '#999999')
        ytm = record.get('yield_to_maturity', 0.0)

        rows.append(f"""
        <tr>
            <td class="fund-name">{record.get('fund_name', 'N/A')}</td>
            <td>
                <span class="provider-badge" style="background-color: {color}">
                    {provider.title()}
                </span>
            </td>
            <td class="center">{record.get('fund_maturity', 'N/A')}</td>
            <td class="ytm-value">{ytm:.2f}%</td>
            <td class="isin">{record.get('isin_code', 'N/A')}</td>
            <td class="center">{format_date(record.get('report_date', 'N/A'))}</td>
        </tr>
        """)

    return '\n'.join(rows)


def generate_dashboard_html(records: List[Dict]) -> str:
    """Generate complete HTML document with embedded data and charts"""

    # Transform data for chart
    chart_data = transform_for_chart(records)
    chart_data_json = json.dumps(chart_data, indent=2)

    # Generate table
    table_rows = generate_table_html(records)

    # Metadata
    last_updated = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    fund_count = len(records)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YTM Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}

        header {{
            border-bottom: 3px solid #4ECDC4;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}

        h1 {{
            font-size: 2.5em;
            color: #2c3e50;
            margin-bottom: 10px;
        }}

        .subtitle {{
            font-size: 1.2em;
            color: #7f8c8d;
            margin-bottom: 15px;
        }}

        .metadata {{
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
            margin-top: 15px;
        }}

        .metadata-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            color: #555;
            font-size: 0.95em;
        }}

        .metadata-item strong {{
            color: #333;
        }}

        #scatter-plot {{
            min-height: 500px;
            margin: 30px 0;
            border-radius: 8px;
            overflow: hidden;
        }}

        .data-table {{
            margin-top: 40px;
        }}

        .data-table h2 {{
            font-size: 1.8em;
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
        }}

        thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}

        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 0.95em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        td {{
            padding: 15px;
            border-bottom: 1px solid #e0e0e0;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        .fund-name {{
            font-weight: 600;
            color: #2c3e50;
        }}

        .provider-badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 15px;
            color: white;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .ytm-value {{
            font-weight: 700;
            color: #27ae60;
            font-size: 1.1em;
        }}

        .isin {{
            font-family: 'Courier New', monospace;
            color: #555;
            font-size: 0.9em;
        }}

        .center {{
            text-align: center;
        }}

        footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 20px;
            }}

            h1 {{
                font-size: 1.8em;
            }}

            table {{
                font-size: 0.85em;
            }}

            th, td {{
                padding: 10px 5px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Bond Fund YTM Dashboard</h1>
            <p class="subtitle">Yield-to-Maturity Analysis</p>
            <div class="metadata">
                <div class="metadata-item">
                    <strong>Last Updated:</strong>
                    <span>{last_updated}</span>
                </div>
                <div class="metadata-item">
                    <strong>Funds Tracked:</strong>
                    <span>{fund_count}</span>
                </div>
            </div>
        </header>

        <div id="scatter-plot"></div>

        <div class="data-table">
            <h2>Fund Details</h2>
            <table>
                <thead>
                    <tr>
                        <th>Fund Name</th>
                        <th>Provider</th>
                        <th class="center">Maturity</th>
                        <th>YTM</th>
                        <th>ISIN Code</th>
                        <th class="center">Report Date</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>

        <footer>
            <p>Data source: Internal YTM Database</p>
            <p>Generated by YTM Dashboard Generator</p>
        </footer>
    </div>

    <script>
        // Embedded fund data
        const fundData = {chart_data_json};

        // Plotly scatter plot configuration
        const chartData = [{{
            x: fundData.x,
            y: fundData.y,
            text: fundData.text,
            mode: 'markers',
            type: 'scatter',
            marker: {{
                size: 16,
                color: fundData.colors,
                line: {{
                    color: 'white',
                    width: 3
                }},
                opacity: 0.9
            }},
            hovertemplate:
                '<b>%{{text}}</b><br>' +
                '<b>YTM:</b> %{{y:.2f}}%<br>' +
                '<b>Maturity:</b> %{{x}}<br>' +
                '<b>Provider:</b> ' + fundData.providers + '<br>' +
                '<b>ISIN:</b> ' + fundData.isins + '<br>' +
                '<extra></extra>',
            customdata: fundData.providers.map((provider, i) => [provider, fundData.isins[i]]),
            hovertemplate:
                '<b>%{{text}}</b><br>' +
                '<b>YTM:</b> %{{y:.2f}}%<br>' +
                '<b>Maturity:</b> %{{x}}<br>' +
                '<b>Provider:</b> %{{customdata[0]}}<br>' +
                '<b>ISIN:</b> %{{customdata[1]}}<br>' +
                '<extra></extra>'
        }}];

        const layout = {{
            title: {{
                text: 'Yield-to-Maturity by Fund Maturity',
                font: {{
                    size: 24,
                    color: '#2c3e50',
                    family: 'inherit'
                }}
            }},
            xaxis: {{
                title: 'Maturity Year',
                dtick: 1,
                gridcolor: '#e0e0e0',
                gridwidth: 1,
                zeroline: false,
                tickfont: {{ size: 12 }}
            }},
            yaxis: {{
                title: 'Yield-to-Maturity (%)',
                tickformat: '.2f',
                gridcolor: '#e0e0e0',
                gridwidth: 1,
                zeroline: false,
                tickfont: {{ size: 12 }}
            }},
            hovermode: 'closest',
            plot_bgcolor: '#fafafa',
            paper_bgcolor: 'white',
            font: {{
                family: 'inherit',
                color: '#333'
            }},
            margin: {{
                l: 60,
                r: 40,
                t: 80,
                b: 60
            }}
        }};

        const config = {{
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['lasso2d', 'select2d'],
            displaylogo: false,
            toImageButtonOptions: {{
                format: 'png',
                filename: 'ytm_dashboard',
                height: 600,
                width: 1000
            }}
        }};

        Plotly.newPlot('scatter-plot', chartData, layout, config);
    </script>
</body>
</html>
"""

    return html


def main():
    """Main entry point"""
    print("\n" + "=" * 60)
    print("YTM DASHBOARD GENERATOR")
    print("=" * 60 + "\n")

    # Query database
    print("📊 Querying database...")
    records = get_ytm_data()

    if not records:
        print("❌ No data to display. Run main.py first to collect data.")
        sys.exit(1)

    # Generate HTML
    print("🎨 Generating dashboard...")
    html_content = generate_dashboard_html(records)

    # Write to file
    output_path = os.path.join(os.path.dirname(__file__), OUTPUT_PATH)

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        file_size = os.path.getsize(output_path)
        print(f"✅ Dashboard generated successfully!")
        print(f"📄 File: {output_path}")
        print(f"💾 Size: {file_size:,} bytes")
        print(f"\n🌐 Open in browser:")
        print(f"   open {output_path}")
        print("=" * 60 + "\n")

    except IOError as e:
        print(f"❌ Error writing file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
