import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.services.weather_service import WeatherService

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

MAJOR_INDIAN_CITIES = [
    "Delhi",
    "Mumbai",
    "Bangalore",
    "Kolkata",
    "Chennai",
    "Hyderabad",
    "Pune",
    "Ahmedabad",
    "Jaipur",
    "Lucknow",
    "Indore",
    "Chandigarh",
    "Surat",
    "Visakhapatnam",
    "Kochi"
]

async def fetch_weather_data():
    """Fetch weather data for all major Indian cities."""
    service = WeatherService()
    weather_data = []
    
    print("Fetching weather data for major Indian cities...\n")
    for city in MAJOR_INDIAN_CITIES:
        try:
            result = await service.get_current_weather(city)
            if result:
                weather_data.append({
                    "city": result.city,
                    "temperature": f"{result.temperature}°C",
                    "feels_like": f"{result.feels_like}°C",
                    "description": result.description.capitalize(),
                    "humidity": f"{result.humidity}%",
                    "wind_speed": f"{result.wind_speed} m/s"
                })
                print(f"[OK] {city}")
            else:
                print(f"[FAIL] {city} - No data")
        except Exception as e:
            print(f"[FAIL] {city} - Error: {str(e)}")
    
    return weather_data

def create_weather_pdf(weather_data, filename="Indian_Cities_Weather.pdf"):
    """Create a PDF with weather data."""
    
    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#666666'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    title = Paragraph("🌤️ Weather Report - Major Indian Cities", title_style)
    story.append(title)
    
    timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    subtitle = Paragraph(f"Generated on: {timestamp}", subtitle_style)
    story.append(subtitle)
    
    story.append(Spacer(1, 0.3*inch))
    
    table_data = [
        ["City", "Temperature", "Feels Like", "Description", "Humidity", "Wind Speed"]
    ]
    
    for data in weather_data:
        table_data.append([
            data["city"],
            data["temperature"],
            data["feels_like"],
            data["description"],
            data["humidity"],
            data["wind_speed"]
        ])
    
    table = Table(table_data, colWidths=[1.2*inch, 1.1*inch, 1.1*inch, 1.3*inch, 0.9*inch, 1.0*inch])
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(table)
    
    story.append(Spacer(1, 0.3*inch))
    
    footer_text = f"<b>Total Cities:</b> {len(weather_data)} | <b>Data Source:</b> OpenWeatherMap API | <b>Report Type:</b> Real-time Weather Data"
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#999999'),
        alignment=TA_CENTER
    )
    story.append(Paragraph(footer_text, footer_style))
    
    doc.build(story)
    print(f"\n[SUCCESS] PDF created successfully: {filename}")
    print(f"[SUCCESS] File size: {len(table_data)} records")
    return filename

async def main():
    """Main function to generate weather PDF."""
    print("=" * 70)
    print("  Weather Report Generator - Major Indian Cities")
    print("=" * 70)
    print()
    
    weather_data = await fetch_weather_data()
    
    if weather_data:
        print(f"\n[SUCCESS] Successfully fetched weather for {len(weather_data)} cities")
        pdf_file = create_weather_pdf(weather_data)
        print(f"\n[SUCCESS] PDF file created: {pdf_file}")
        print(f"[SUCCESS] Location: {pdf_file}")
        print("\nYou can now:")
        print("1. Upload this PDF to the Streamlit UI")
        print("2. Ask questions about the weather data")
        print("3. Use it for RAG-based document queries")
    else:
        print("\n[ERROR] Failed to fetch weather data")
        print("Please check your API keys in .env file")

if __name__ == "__main__":
    asyncio.run(main())
