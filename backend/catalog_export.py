#!/usr/bin/env python3
"""
Collectibles Catalog Export Tool
Exports catalog data to CSV, JSON, or platform-specific formats
Authority Level 11.0 | Commander Bobby Don McWilliams II
"""

import json
import csv
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

class CollectiblesCatalog:
    """Main catalog management class"""
    
    def __init__(self, catalog_path: Optional[str] = None):
        self.items: List[Dict[str, Any]] = []
        self.catalog_path = catalog_path
        if catalog_path and os.path.exists(catalog_path):
            self.load_catalog(catalog_path)
    
    def add_item(self, item: Dict[str, Any]) -> None:
        """Add item to catalog"""
        item['catalog_id'] = self._generate_id()
        item['added_date'] = datetime.now().isoformat()
        self.items.append(item)
    
    def _generate_id(self) -> str:
        """Generate unique catalog ID"""
        return f"COL-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self.items):04d}"
    
    def load_catalog(self, path: str) -> None:
        """Load catalog from JSON file"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.items = data.get('items', [])
    
    def save_catalog(self, path: str) -> None:
        """Save catalog to JSON file"""
        data = {
            'catalog_version': '1.0',
            'export_date': datetime.now().isoformat(),
            'item_count': len(self.items),
            'items': self.items
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Saved {len(self.items)} items to {path}")
    
    def export_csv(self, path: str, item_type: Optional[str] = None) -> None:
        """Export catalog to CSV"""
        items = self.items
        if item_type:
            items = [i for i in items if i.get('type') == item_type]
        
        if not items:
            print("No items to export")
            return
        
        # Get all unique keys across items
        all_keys = set()
        for item in items:
            all_keys.update(item.keys())
        
        fieldnames = sorted(list(all_keys))
        
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(items)
        
        print(f"✓ Exported {len(items)} items to {path}")
    
    def export_clz(self, path: str) -> None:
        """Export to CLZ Comics format (XML)"""
        comics = [i for i in self.items if i.get('type') == 'comic_book']
        
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content += '<comiclist>\n'
        
        for comic in comics:
            xml_content += '  <comic>\n'
            xml_content += f'    <series>{comic.get("title", "")}</series>\n'
            xml_content += f'    <issue>{comic.get("issue_number", "")}</issue>\n'
            xml_content += f'    <publisher>{comic.get("publisher", "")}</publisher>\n'
            xml_content += f'    <coverdate>{comic.get("cover_date", "")}</coverdate>\n'
            xml_content += f'    <grade>{comic.get("cgc_grade") or comic.get("raw_grade", "")}</grade>\n'
            xml_content += f'    <value>{comic.get("market_value", "")}</value>\n'
            xml_content += f'    <notes>{comic.get("notes", "")}</notes>\n'
            xml_content += '  </comic>\n'
        
        xml_content += '</comiclist>'
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        print(f"✓ Exported {len(comics)} comics to CLZ format: {path}")
    
    def export_beckett(self, path: str) -> None:
        """Export to Beckett inventory format"""
        cards = [i for i in self.items if 'card' in i.get('type', '')]
        
        beckett_data = []
        for card in cards:
            beckett_data.append({
                'Player': card.get('player_name') or card.get('subject_name', ''),
                'Year': card.get('year', ''),
                'Brand': card.get('brand', ''),
                'Set': card.get('set_name', ''),
                'Card #': card.get('card_number', ''),
                'Subset': card.get('subset', ''),
                'RC': 'Yes' if card.get('rookie') else '',
                'Auto': 'Yes' if card.get('auto') else '',
                'Mem': 'Yes' if card.get('relic') else '',
                'Serial #': card.get('serial_number', ''),
                'Grade': card.get('psa_grade') or card.get('bgs_grade') or card.get('raw_grade', ''),
                'Cert #': card.get('cert_number', ''),
                'Cost': card.get('purchase_price', ''),
                'Value': card.get('market_value', '')
            })
        
        with open(path, 'w', newline='', encoding='utf-8') as f:
            if beckett_data:
                writer = csv.DictWriter(f, fieldnames=beckett_data[0].keys())
                writer.writeheader()
                writer.writerows(beckett_data)
        
        print(f"✓ Exported {len(cards)} cards to Beckett format: {path}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get catalog summary statistics"""
        type_counts = {}
        total_value = 0
        total_cost = 0
        
        for item in self.items:
            item_type = item.get('type', 'unknown')
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
            
            if item.get('market_value'):
                total_value += float(str(item['market_value']).replace('$', '').replace(',', ''))
            if item.get('purchase_price'):
                total_cost += float(str(item['purchase_price']).replace('$', '').replace(',', ''))
        
        return {
            'total_items': len(self.items),
            'items_by_type': type_counts,
            'total_market_value': f"${total_value:,.2f}",
            'total_cost': f"${total_cost:,.2f}",
            'roi': f"{((total_value - total_cost) / total_cost * 100):.1f}%" if total_cost > 0 else "N/A"
        }
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search catalog items"""
        query_lower = query.lower()
        results = []
        
        for item in self.items:
            for value in item.values():
                if isinstance(value, str) and query_lower in value.lower():
                    results.append(item)
                    break
        
        return results


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Collectibles Catalog Export Tool')
    parser.add_argument('catalog', help='Path to catalog JSON file')
    parser.add_argument('--export', choices=['csv', 'json', 'clz', 'beckett'], 
                       help='Export format')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--type', help='Filter by item type')
    parser.add_argument('--summary', action='store_true', help='Show catalog summary')
    parser.add_argument('--search', help='Search catalog')
    
    args = parser.parse_args()
    
    catalog = CollectiblesCatalog(args.catalog)
    
    if args.summary:
        summary = catalog.get_summary()
        print("\n=== CATALOG SUMMARY ===")
        print(f"Total Items: {summary['total_items']}")
        print(f"Total Value: {summary['total_market_value']}")
        print(f"Total Cost: {summary['total_cost']}")
        print(f"ROI: {summary['roi']}")
        print("\nItems by Type:")
        for item_type, count in summary['items_by_type'].items():
            print(f"  {item_type}: {count}")
    
    if args.search:
        results = catalog.search(args.search)
        print(f"\nFound {len(results)} items matching '{args.search}'")
        for item in results[:10]:
            print(f"  - {item.get('title') or item.get('player_name') or item.get('name', 'Unknown')}")
    
    if args.export:
        output = args.output or f"catalog_export.{args.export}"
        
        if args.export == 'csv':
            catalog.export_csv(output, args.type)
        elif args.export == 'json':
            catalog.save_catalog(output)
        elif args.export == 'clz':
            catalog.export_clz(output)
        elif args.export == 'beckett':
            catalog.export_beckett(output)


if __name__ == '__main__':
    main()
