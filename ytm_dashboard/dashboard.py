#!/usr/bin/env python3
"""
YTM Dashboard Generator
Generates static HTML visualization of yield-to-maturity data
"""

import argparse
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


def get_ytm_data(report_date: str = None) -> List[Dict]:
    """Query database for YTM records

    Args:
        report_date: Optional specific date (YYYY-MM-01).
                    If None, gets latest records.

    Returns:
        List of fund records
    """
    try:
        # Use absolute path
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'ytm_data.db')
        db = DatabaseManager(db_path)

        if report_date:
            records = db.get_records_by_date(report_date)
            print(f"✅ Loaded {len(records)} records for {report_date}")
        else:
            records = db.get_latest_records()
            print(f"✅ Loaded {len(records)} latest records")

        if not records:
            print("⚠️  Warning: No data found in database")
            return []

        return records

    except Exception as e:
        print(f"❌ Error querying database: {e}")
        return []


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


def get_output_filename(report_date: str = None) -> str:
    """Generate filename based on report date

    Args:
        report_date: Date in YYYY-MM-01 format

    Returns:
        Filename like 'october_2025.html' or 'index.html'
    """
    if report_date:
        # Convert '2025-10-01' to 'october_2025.html'
        dt = datetime.strptime(report_date, '%Y-%m-%d')
        return dt.strftime('%B_%Y').lower() + '.html'
    else:
        return 'index.html'  # Latest month as index


def get_all_report_dates() -> List[str]:
    """Get all unique report dates from database"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'ytm_data.db')
        db = DatabaseManager(db_path)

        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT report_date FROM fund_ytm_data ORDER BY report_date")
        dates = [row[0] for row in cursor.fetchall()]
        conn.close()

        return dates
    except Exception as e:
        print(f"❌ Error querying dates: {e}")
        return []


def generate_all_dashboards(quiet: bool = False) -> bool:
    """
    Generate dashboards for all months in database + latest index.html

    Args:
        quiet: If True, suppress console output

    Returns:
        True if successful, False if errors occurred
    """
    try:
        all_dates = get_all_report_dates()

        if not all_dates:
            if not quiet:
                print("❌ No data in database")
            return False

        if not quiet:
            print(f"\n📊 Generating dashboards for {len(all_dates)} months...")

        success_count = 0

        # Generate dashboard for each historical month
        for date in all_dates:
            try:
                records = get_ytm_data(report_date=date)
                if not records:
                    continue

                html_content = generate_dashboard_html(records, report_date=date)
                filename = get_output_filename(date)
                output_path = os.path.join(os.path.dirname(__file__), filename)

                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                if not quiet:
                    file_size = os.path.getsize(output_path)
                    print(f"  ✅ {filename} ({file_size:,} bytes)")

                success_count += 1

            except Exception as e:
                if not quiet:
                    print(f"  ❌ Error generating {date}: {e}")

        # Generate index.html with latest data
        try:
            latest_records = get_ytm_data()
            latest_html = generate_dashboard_html(latest_records)
            index_path = os.path.join(os.path.dirname(__file__), 'index.html')

            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(latest_html)

            if not quiet:
                print(f"  ✅ index.html (latest)")

            success_count += 1

        except Exception as e:
            if not quiet:
                print(f"  ❌ Error generating index.html: {e}")

        if not quiet:
            print(f"\n✅ Generated {success_count} dashboard files")

        return success_count > 0

    except Exception as e:
        if not quiet:
            print(f"❌ Dashboard generation failed: {e}")
        return False


def generate_latest_dashboard(quiet: bool = False) -> bool:
    """
    Generate only the latest dashboard (index.html)

    Args:
        quiet: If True, suppress console output

    Returns:
        True if successful, False if errors occurred
    """
    try:
        records = get_ytm_data()

        if not records:
            if not quiet:
                print("❌ No data in database")
            return False

        html_content = generate_dashboard_html(records)
        output_path = os.path.join(os.path.dirname(__file__), 'index.html')

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        if not quiet:
            file_size = os.path.getsize(output_path)
            print(f"✅ Dashboard generated: index.html ({file_size:,} bytes)")

        return True

    except Exception as e:
        if not quiet:
            print(f"❌ Dashboard generation failed: {e}")
        return False


def generate_historical_nav(all_dates: List[str], current_date: str = None) -> str:
    """Generate historical month navigation links

    Args:
        all_dates: List of all report dates
        current_date: Currently displayed date (to highlight)

    Returns:
        HTML navigation component
    """
    if len(all_dates) <= 1:
        return ""  # Don't show nav if only one month

    links = []
    for date in sorted(all_dates):  # Chronological order (oldest to newest)
        dt = datetime.strptime(date, '%Y-%m-%d')
        month_name = dt.strftime('%B %Y')
        filename = dt.strftime('%B_%Y').lower() + '.html'

        # Highlight current month
        css_class = 'month-link active' if date == current_date else 'month-link'
        links.append(f'<a href="{filename}" class="{css_class}">{month_name}</a>')

    return f"""
    <div class="historical-nav">
        <h3>📅 Historical Dashboards</h3>
        <div class="month-links">
            {' '.join(links)}
        </div>
    </div>
    """


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


def generate_dashboard_html(records: List[Dict], report_date: str = None) -> str:
    """Generate complete HTML document with embedded data and charts

    Args:
        records: List of fund records
        report_date: Report date for this dashboard (YYYY-MM-01)

    Returns:
        Complete HTML document string
    """

    # Transform data for chart
    chart_data = transform_for_chart(records)
    chart_data_json = json.dumps(chart_data, indent=2)

    # Generate table
    table_rows = generate_table_html(records)

    # Get all dates for navigation
    all_dates = get_all_report_dates()
    historical_nav = generate_historical_nav(all_dates, report_date)

    # Determine title based on report date
    if report_date:
        dt = datetime.strptime(report_date, '%Y-%m-%d')
        title_suffix = f" - {dt.strftime('%B %Y')}"
    else:
        title_suffix = " - Latest"

    # Metadata
    last_updated = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    fund_count = len(records)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YTM Dashboard{title_suffix}</title>
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

        .historical-nav {{
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}

        .historical-nav h3 {{
            margin-bottom: 15px;
            color: #2c3e50;
            font-size: 1.2em;
        }}

        .month-links {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .month-link {{
            padding: 8px 16px;
            background: white;
            border: 2px solid #4ECDC4;
            border-radius: 6px;
            text-decoration: none;
            color: #2c3e50;
            font-weight: 500;
            transition: all 0.3s ease;
        }}

        .month-link:hover {{
            background: #4ECDC4;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}

        .month-link.active {{
            background: #4ECDC4;
            color: white;
            font-weight: 700;
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

        {historical_nav}

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
            text: fundData.y.map(val => val.toFixed(2) + '%'),  // Format as percentage
            mode: 'markers+text',  // Add text labels
            type: 'scatter',
            textposition: 'top center',  // Position above dots
            textfont: {{
                size: 11,
                color: '#333',
                family: 'inherit'
            }},
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
                tickfont: {{ size: 12 }},
                range: [0, Math.max(...fundData.y) + 1]  // Max value + 1%
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
                t: 100,  // Increased for percentage labels above dots
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
    parser = argparse.ArgumentParser(description='Generate YTM dashboard')
    parser.add_argument('--date', help='Report date (YYYY-MM-01) for specific month')
    parser.add_argument('--all', action='store_true', help='Generate dashboards for all months')
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("YTM DASHBOARD GENERATOR")
    print("=" * 60 + "\n")

    if args.all:
        # Generate dashboard for each month in database
        all_dates = get_all_report_dates()

        if not all_dates:
            print("❌ No data in database")
            sys.exit(1)

        print(f"📊 Generating dashboards for {len(all_dates)} months...\n")

        for date in all_dates:
            print(f"📅 {date}...")
            records = get_ytm_data(report_date=date)

            if not records:
                print(f"  ⚠️  No data for {date}, skipping")
                continue

            html_content = generate_dashboard_html(records, report_date=date)
            filename = get_output_filename(date)
            output_path = os.path.join(os.path.dirname(__file__), filename)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            file_size = os.path.getsize(output_path)
            print(f"  ✅ {filename} ({file_size:,} bytes)")

        # Also generate index.html with latest data
        print(f"\n📅 Latest (index.html)...")
        latest_records = get_ytm_data()
        latest_html = generate_dashboard_html(latest_records)
        index_path = os.path.join(os.path.dirname(__file__), 'index.html')

        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(latest_html)

        print(f"  ✅ index.html")
        print("\n" + "=" * 60)
        print(f"✅ Generated {len(all_dates) + 1} dashboard files")
        print("=" * 60 + "\n")

    elif args.date:
        # Generate dashboard for specific month
        print(f"📊 Generating dashboard for {args.date}...\n")
        records = get_ytm_data(report_date=args.date)

        if not records:
            print(f"❌ No data for {args.date}")
            sys.exit(1)

        html_content = generate_dashboard_html(records, report_date=args.date)
        filename = get_output_filename(args.date)
        output_path = os.path.join(os.path.dirname(__file__), filename)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        file_size = os.path.getsize(output_path)
        print(f"✅ Dashboard generated: {filename} ({file_size:,} bytes)")
        print("=" * 60 + "\n")

    else:
        # Generate latest dashboard (default behavior)
        print("📊 Generating latest dashboard...\n")
        records = get_ytm_data()

        if not records:
            print("❌ No data in database")
            sys.exit(1)

        html_content = generate_dashboard_html(records)
        output_path = os.path.join(os.path.dirname(__file__), OUTPUT_PATH)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        file_size = os.path.getsize(output_path)
        print(f"✅ Dashboard generated: {OUTPUT_PATH} ({file_size:,} bytes)")
        print(f"📄 File: {output_path}")
        print(f"\n🌐 Open in browser:")
        print(f"   open {output_path}")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
