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

# Provider color scheme - muted, sophisticated palette
PROVIDER_COLORS = {
    'carmignac': '#E07A5F',    # Terracotta
    'sycomore': '#81B29A',     # Sage green
    'rothschild': '#5B8BA0'    # Steel blue
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
        'colors': [PROVIDER_COLORS.get(r['provider'].lower(), '#999999') for r in records],
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
        color = PROVIDER_COLORS.get(provider.lower(), '#999999')
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
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #fafafa;
            color: #1a1a1a;
            line-height: 1.7;
            padding: 40px 20px;
        }}

        .container {{
            max-width: 1100px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 60px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 4px 12px rgba(0, 0, 0, 0.03);
        }}

        header {{
            padding-bottom: 40px;
            margin-bottom: 40px;
            border-bottom: 1px solid #eee;
        }}

        h1 {{
            font-size: 1.75em;
            font-weight: 600;
            color: #1a1a1a;
            margin-bottom: 8px;
            letter-spacing: -0.02em;
        }}

        .subtitle {{
            font-size: 1em;
            color: #888;
            font-weight: 400;
        }}

        .metadata {{
            display: flex;
            gap: 32px;
            flex-wrap: wrap;
            margin-top: 24px;
        }}

        .metadata-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            color: #666;
            font-size: 0.875em;
        }}

        .metadata-item strong {{
            color: #1a1a1a;
            font-weight: 500;
        }}

        #scatter-plot {{
            min-height: 480px;
            margin: 48px 0;
            border-radius: 12px;
            border: 1px solid #eee;
            overflow: hidden;
        }}

        .data-table {{
            margin-top: 56px;
        }}

        .data-table h2 {{
            font-size: 1.25em;
            font-weight: 600;
            color: #1a1a1a;
            margin-bottom: 24px;
            letter-spacing: -0.01em;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
        }}

        thead {{
            background: #f8f8f8;
        }}

        th {{
            padding: 14px 16px;
            text-align: left;
            font-weight: 500;
            font-size: 0.75em;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #666;
            border-bottom: 1px solid #eee;
        }}

        td {{
            padding: 16px;
            border-bottom: 1px solid #f0f0f0;
            font-size: 0.9em;
        }}

        tbody tr {{
            transition: background 0.15s ease;
        }}

        tbody tr:hover {{
            background: #fafafa;
        }}

        tbody tr:last-child td {{
            border-bottom: none;
        }}

        .fund-name {{
            font-weight: 500;
            color: #1a1a1a;
        }}

        .provider-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.7em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            opacity: 0.9;
        }}

        .ytm-value {{
            font-weight: 600;
            color: #1a1a1a;
            font-size: 1em;
            font-variant-numeric: tabular-nums;
        }}

        .isin {{
            font-family: 'SF Mono', 'Menlo', 'Monaco', monospace;
            color: #888;
            font-size: 0.8em;
            letter-spacing: 0.02em;
        }}

        .center {{
            text-align: center;
        }}

        footer {{
            margin-top: 56px;
            padding-top: 24px;
            border-top: 1px solid #eee;
            text-align: center;
            color: #999;
            font-size: 0.8em;
        }}

        footer p {{
            margin: 4px 0;
        }}

        .historical-nav {{
            margin: 32px 0;
            padding: 24px;
            background: #fafafa;
            border-radius: 10px;
            border: 1px solid #eee;
        }}

        .historical-nav h3 {{
            margin-bottom: 16px;
            color: #666;
            font-size: 0.8em;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .month-links {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .month-link {{
            padding: 8px 14px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 6px;
            text-decoration: none;
            color: #444;
            font-size: 0.85em;
            font-weight: 500;
            transition: all 0.2s ease;
        }}

        .month-link:hover {{
            border-color: #1a1a1a;
            color: #1a1a1a;
        }}

        .month-link.active {{
            background: #1a1a1a;
            border-color: #1a1a1a;
            color: white;
        }}

        @media (max-width: 768px) {{
            body {{
                padding: 20px 12px;
            }}

            .container {{
                padding: 32px 24px;
                border-radius: 12px;
            }}

            h1 {{
                font-size: 1.4em;
            }}

            table {{
                font-size: 0.85em;
            }}

            th, td {{
                padding: 12px 8px;
            }}

            .metadata {{
                gap: 16px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Bond Fund YTM Dashboard</h1>
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
                size: 14,
                color: fundData.colors,
                line: {{
                    color: 'white',
                    width: 2
                }},
                opacity: 0.85
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
                    size: 18,
                    color: '#1a1a1a',
                    family: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
                    weight: 600
                }},
                x: 0,
                xanchor: 'left',
                y: 0.98
            }},
            xaxis: {{
                title: {{
                    text: 'Maturity Year',
                    font: {{ size: 12, color: '#666' }}
                }},
                dtick: 1,
                gridcolor: '#f0f0f0',
                gridwidth: 1,
                zeroline: false,
                tickfont: {{ size: 11, color: '#888' }},
                linecolor: '#eee'
            }},
            yaxis: {{
                title: {{
                    text: 'Yield-to-Maturity (%)',
                    font: {{ size: 12, color: '#666' }}
                }},
                tickformat: '.2f',
                gridcolor: '#f0f0f0',
                gridwidth: 1,
                zeroline: false,
                tickfont: {{ size: 11, color: '#888' }},
                linecolor: '#eee',
                range: [0, Math.max(...fundData.y) + 1]
            }},
            hovermode: 'closest',
            plot_bgcolor: 'white',
            paper_bgcolor: 'white',
            font: {{
                family: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
                color: '#1a1a1a'
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
