"""
Investor Portal Generator
Generates static HTML portfolio for comic collections
"""

import os
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader
import base64

logger = logging.getLogger(__name__)


class PortalGenerator:
    """
    Static HTML Portfolio Generator

    Features:
    - Responsive design
    - Image optimization
    - SEO-friendly structure
    - No JavaScript dependencies (works offline)
    - Netlify-ready deployment
    """

    def __init__(
        self,
        template_dir: str = "P:/SOVEREIGN_APPS/collectibles_grading_system/static_export/templates",
        output_dir: str = "P:/SOVEREIGN_APPS/collectibles_grading_system/static_export/output"
    ):
        self.template_dir = Path(template_dir)
        self.output_dir = Path(output_dir)

        # Initialize Jinja2
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True
        )

        # Register filters
        self.env.filters['currency'] = self._format_currency
        self.env.filters['grade_label'] = self._grade_to_label
        self.env.filters['grade_class'] = self._grade_to_class

    def generate(
        self,
        comics: List[Dict],
        collection_name: str = "Comic Collection",
        owner_name: str = "",
        include_images: bool = True,
        include_pricing: bool = True
    ) -> str:
        """
        Generate complete portal

        Args:
            comics: List of comic dictionaries
            collection_name: Name of the collection
            owner_name: Owner's name
            include_images: Include comic images
            include_pricing: Include pricing information

        Returns:
            Path to generated portal
        """
        # Prepare output directory
        self._prepare_output()

        # Calculate statistics
        stats = self._calculate_stats(comics)

        # Generate pages
        self._generate_index(comics, collection_name, owner_name, stats)
        self._generate_gallery(comics)
        self._generate_detail_pages(comics, include_images, include_pricing)
        self._generate_stats_page(stats)

        # Copy assets
        self._copy_assets()

        # Copy images if requested
        if include_images:
            self._copy_images(comics)

        # Generate sitemap
        self._generate_sitemap(comics)

        # Generate Netlify config
        self._generate_netlify_config()

        logger.info(f"Portal generated at: {self.output_dir}")
        return str(self.output_dir)

    def _prepare_output(self):
        """Prepare output directory"""
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)

        self.output_dir.mkdir(parents=True)
        (self.output_dir / "images").mkdir()
        (self.output_dir / "comics").mkdir()
        (self.output_dir / "css").mkdir()

    def _calculate_stats(self, comics: List[Dict]) -> Dict:
        """Calculate collection statistics"""
        graded = [c for c in comics if c.get('consensus_grade')]
        priced = [c for c in comics if c.get('consensus_price')]

        stats = {
            'total_comics': len(comics),
            'graded_comics': len(graded),
            'total_value': sum(c['consensus_price'] for c in priced),
            'average_grade': sum(c['consensus_grade'] for c in graded) / len(graded) if graded else 0,
            'highest_grade': max((c['consensus_grade'] for c in graded), default=0),
            'highest_value': max((c['consensus_price'] for c in priced), default=0),
            'publishers': {},
            'grade_distribution': {},
            'generated_at': datetime.utcnow().isoformat()
        }

        # Publisher breakdown
        for comic in comics:
            pub = comic.get('publisher', 'Unknown')
            stats['publishers'][pub] = stats['publishers'].get(pub, 0) + 1

        # Grade distribution
        for comic in graded:
            grade = comic['consensus_grade']
            if grade >= 9.0:
                bucket = '9.0+'
            elif grade >= 8.0:
                bucket = '8.0-8.9'
            elif grade >= 6.0:
                bucket = '6.0-7.9'
            elif grade >= 4.0:
                bucket = '4.0-5.9'
            else:
                bucket = 'Below 4.0'
            stats['grade_distribution'][bucket] = stats['grade_distribution'].get(bucket, 0) + 1

        return stats

    def _generate_index(
        self,
        comics: List[Dict],
        collection_name: str,
        owner_name: str,
        stats: Dict
    ):
        """Generate index.html"""
        template = self.env.get_template('index.html')

        # Get featured comics (highest value)
        featured = sorted(
            [c for c in comics if c.get('consensus_price')],
            key=lambda x: x['consensus_price'],
            reverse=True
        )[:6]

        html = template.render(
            collection_name=collection_name,
            owner_name=owner_name,
            stats=stats,
            featured_comics=featured,
            generated_at=datetime.utcnow().strftime("%B %d, %Y")
        )

        (self.output_dir / "index.html").write_text(html, encoding='utf-8')

    def _generate_gallery(self, comics: List[Dict]):
        """Generate gallery.html"""
        template = self.env.get_template('gallery.html')

        # Sort by grade descending
        sorted_comics = sorted(
            comics,
            key=lambda x: x.get('consensus_grade', 0),
            reverse=True
        )

        html = template.render(
            comics=sorted_comics,
            total=len(comics)
        )

        (self.output_dir / "gallery.html").write_text(html, encoding='utf-8')

    def _generate_detail_pages(
        self,
        comics: List[Dict],
        include_images: bool,
        include_pricing: bool
    ):
        """Generate individual comic detail pages"""
        template = self.env.get_template('comic_detail.html')

        for comic in comics:
            html = template.render(
                comic=comic,
                include_images=include_images,
                include_pricing=include_pricing
            )

            filename = f"comic_{comic['id']}.html"
            (self.output_dir / "comics" / filename).write_text(html, encoding='utf-8')

    def _generate_stats_page(self, stats: Dict):
        """Generate statistics page"""
        template = self.env.get_template('stats.html')

        html = template.render(stats=stats)

        (self.output_dir / "stats.html").write_text(html, encoding='utf-8')

    def _copy_assets(self):
        """Copy CSS and other assets"""
        css_content = self._generate_css()
        (self.output_dir / "css" / "style.css").write_text(css_content, encoding='utf-8')

    def _copy_images(self, comics: List[Dict]):
        """Copy comic images to output"""
        for comic in comics:
            for img_field in ['front_image_path', 'back_image_path']:
                img_path = comic.get(img_field)
                if img_path and Path(img_path).exists():
                    dest = self.output_dir / "images" / Path(img_path).name
                    shutil.copy2(img_path, dest)
                    comic[img_field] = f"images/{Path(img_path).name}"

    def _generate_sitemap(self, comics: List[Dict]):
        """Generate sitemap.xml"""
        urls = ['index.html', 'gallery.html', 'stats.html']
        urls.extend([f"comics/comic_{c['id']}.html" for c in comics])

        sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

        for url in urls:
            sitemap += f'  <url><loc>{url}</loc></url>\n'

        sitemap += '</urlset>'

        (self.output_dir / "sitemap.xml").write_text(sitemap, encoding='utf-8')

    def _generate_netlify_config(self):
        """Generate netlify.toml for deployment"""
        config = """[build]
  publish = "."

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-XSS-Protection = "1; mode=block"
    X-Content-Type-Options = "nosniff"
"""
        (self.output_dir / "netlify.toml").write_text(config, encoding='utf-8')

    def _generate_css(self) -> str:
        """Generate portal CSS"""
        return """
/* Comic Collection Portal Stylesheet */
:root {
    --bg-dark: #0f172a;
    --bg-card: #1e293b;
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --accent: #6366f1;
    --success: #22c55e;
    --warning: #f59e0b;
    --danger: #ef4444;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: var(--bg-dark);
    color: var(--text-primary);
    line-height: 1.6;
}

.container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }

/* Header */
header {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    padding: 60px 0;
    text-align: center;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}

header h1 {
    font-size: 3rem;
    margin-bottom: 10px;
    background: linear-gradient(135deg, var(--accent), #818cf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

header .subtitle { color: var(--text-secondary); font-size: 1.2rem; }

/* Navigation */
nav {
    background: var(--bg-card);
    padding: 15px 0;
    position: sticky;
    top: 0;
    z-index: 100;
}

nav ul { list-style: none; display: flex; justify-content: center; gap: 30px; }
nav a {
    color: var(--text-secondary);
    text-decoration: none;
    font-weight: 500;
    transition: color 0.2s;
}
nav a:hover { color: var(--accent); }

/* Stats Grid */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    padding: 40px 0;
}

.stat-card {
    background: var(--bg-card);
    padding: 25px;
    border-radius: 12px;
    text-align: center;
}

.stat-value {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--accent);
}

.stat-label { color: var(--text-secondary); margin-top: 5px; }

/* Comics Grid */
.comics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 25px;
    padding: 40px 0;
}

.comic-card {
    background: var(--bg-card);
    border-radius: 16px;
    overflow: hidden;
    transition: transform 0.3s, box-shadow 0.3s;
}

.comic-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 40px rgba(99, 102, 241, 0.2);
}

.comic-image {
    height: 320px;
    background: #334155;
    position: relative;
}

.comic-image img { width: 100%; height: 100%; object-fit: cover; }

.grade-badge {
    position: absolute;
    top: 12px;
    right: 12px;
    padding: 6px 14px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 1.1rem;
}

.grade-high { background: var(--success); color: white; }
.grade-medium { background: var(--warning); color: black; }
.grade-low { background: var(--danger); color: white; }

.comic-info { padding: 20px; }
.comic-info h3 { font-size: 1.2rem; margin-bottom: 8px; }
.comic-info .publisher { color: var(--text-secondary); font-size: 0.9rem; }
.comic-info .price { color: var(--success); font-weight: 600; margin-top: 10px; font-size: 1.1rem; }

/* Detail Page */
.comic-detail {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 40px;
    padding: 40px 0;
}

.detail-images img {
    width: 100%;
    border-radius: 12px;
    margin-bottom: 20px;
}

.detail-info h1 { font-size: 2.5rem; margin-bottom: 20px; }
.detail-grade {
    font-size: 4rem;
    font-weight: 700;
    color: var(--accent);
}

.defects-list {
    background: rgba(239, 68, 68, 0.1);
    border-radius: 8px;
    padding: 15px;
    margin-top: 20px;
}

.defect-item {
    padding: 8px 0;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}

/* Footer */
footer {
    text-align: center;
    padding: 40px;
    color: var(--text-secondary);
    border-top: 1px solid rgba(255,255,255,0.1);
}

/* Responsive */
@media (max-width: 768px) {
    header h1 { font-size: 2rem; }
    .comic-detail { grid-template-columns: 1fr; }
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
}
"""

    @staticmethod
    def _format_currency(value):
        """Format number as currency"""
        if value is None:
            return "N/A"
        return f"${value:,.2f}"

    @staticmethod
    def _grade_to_label(grade):
        """Convert grade to label"""
        if grade is None:
            return "Ungraded"
        if grade >= 9.8:
            return "Near Mint/Mint"
        elif grade >= 9.0:
            return "Near Mint"
        elif grade >= 8.0:
            return "Very Fine"
        elif grade >= 6.0:
            return "Fine"
        elif grade >= 4.0:
            return "Very Good"
        elif grade >= 2.0:
            return "Good"
        return "Poor"

    @staticmethod
    def _grade_to_class(grade):
        """Get CSS class for grade"""
        if grade is None:
            return ""
        if grade >= 8.0:
            return "grade-high"
        elif grade >= 5.0:
            return "grade-medium"
        return "grade-low"


# Convenience function
def generate_portal(comics: List[Dict], **kwargs) -> str:
    """Generate investor portal"""
    generator = PortalGenerator()
    return generator.generate(comics, **kwargs)
