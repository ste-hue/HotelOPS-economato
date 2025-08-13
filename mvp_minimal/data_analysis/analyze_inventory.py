import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

class InventoryAnalyzer:
    """Analyze hotel inventory data from the economato system."""

    def __init__(self, data_path: str = None):
        """Initialize the analyzer with optional data path."""
        self.data_path = data_path
        self.df = None
        self.column_names = [
            'index', 'product_code', 'description', 'category', 'subcategory',
            'unit', 'supplier', 'qty1', 'qty2_with_unit', 'price',
            'col10', 'col11', 'col12', 'col13', 'consumption1', 'consumption2',
            'consumption3', 'consumption4', 'col18', 'daily_consumption',
            'col20', 'final_qty'
        ]

    def load_data(self, data_string: str = None):
        """Load data from string or file."""
        if data_string:
            # Parse the tab-separated data
            lines = data_string.strip().split('\n')
            data = []
            for line in lines:
                parts = line.split('\t')
                data.append(parts)

            self.df = pd.DataFrame(data, columns=self.column_names)
            self._clean_data()
        elif self.data_path:
            self.df = pd.read_csv(self.data_path, sep='\t', names=self.column_names)
            self._clean_data()

    def _clean_data(self):
        """Clean and convert data types."""
        # Convert numeric columns
        numeric_cols = ['index', 'qty1', 'price', 'col10', 'col11', 'col12',
                       'col13', 'col18', 'col20']

        for col in numeric_cols:
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce')

        # Extract numeric values from qty2_with_unit
        self.df['qty2'] = self.df['qty2_with_unit'].str.extract(r'([\d.]+)').astype(float)

        # Extract numeric values from consumption columns
        for col in ['consumption1', 'consumption2', 'consumption3', 'consumption4',
                   'daily_consumption', 'final_qty']:
            if col in self.df.columns:
                self.df[f'{col}_numeric'] = self.df[col].str.extract(r'([\d.]+)').astype(float)

    def get_summary_statistics(self) -> Dict:
        """Get summary statistics for the inventory."""
        stats = {
            'total_products': len(self.df),
            'unique_categories': self.df['category'].nunique(),
            'unique_suppliers': self.df['supplier'].nunique(),
            'total_inventory_value': self.df['price'].sum(),
            'avg_price': self.df['price'].mean(),
            'products_with_stock': (self.df['qty1'] > 0).sum(),
            'products_without_stock': (self.df['qty1'] == 0).sum()
        }
        return stats

    def analyze_by_category(self) -> pd.DataFrame:
        """Analyze inventory by category."""
        category_analysis = self.df.groupby('category').agg({
            'product_code': 'count',
            'price': ['sum', 'mean'],
            'qty1': 'sum'
        }).round(2)

        category_analysis.columns = ['product_count', 'total_value', 'avg_price', 'total_quantity']
        return category_analysis

    def analyze_by_supplier(self) -> pd.DataFrame:
        """Analyze inventory by supplier."""
        supplier_analysis = self.df.groupby('supplier').agg({
            'product_code': 'count',
            'price': 'sum',
            'qty1': 'sum'
        }).round(2)

        supplier_analysis.columns = ['product_count', 'total_value', 'total_quantity']
        return supplier_analysis.sort_values('total_value', ascending=False)

    def identify_high_value_items(self, top_n: int = 10) -> pd.DataFrame:
        """Identify the most expensive items in inventory."""
        high_value = self.df.nlargest(top_n, 'price')[
            ['product_code', 'description', 'price', 'qty1', 'supplier']
        ]
        high_value['total_value'] = high_value['price'] * high_value['qty1']
        return high_value

    def analyze_stock_status(self) -> Dict:
        """Analyze stock status across categories."""
        stock_status = {}

        for category in self.df['category'].unique():
            cat_data = self.df[self.df['category'] == category]
            stock_status[category] = {
                'in_stock': (cat_data['qty1'] > 0).sum(),
                'out_of_stock': (cat_data['qty1'] == 0).sum(),
                'percentage_stocked': ((cat_data['qty1'] > 0).sum() / len(cat_data) * 100).round(2)
            }

        return stock_status

    def generate_report(self) -> str:
        """Generate a comprehensive inventory report."""
        report = []
        report.append("=" * 60)
        report.append("HOTEL INVENTORY ANALYSIS REPORT")
        report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 60)

        # Summary statistics
        stats = self.get_summary_statistics()
        report.append("\n## SUMMARY STATISTICS")
        report.append(f"Total Products: {stats['total_products']}")
        report.append(f"Unique Categories: {stats['unique_categories']}")
        report.append(f"Unique Suppliers: {stats['unique_suppliers']}")
        report.append(f"Total Inventory Value: €{stats['total_inventory_value']:,.2f}")
        report.append(f"Average Price per Item: €{stats['avg_price']:,.2f}")
        report.append(f"Products in Stock: {stats['products_with_stock']}")
        report.append(f"Products Out of Stock: {stats['products_without_stock']}")

        # Category analysis
        report.append("\n## ANALYSIS BY CATEGORY")
        cat_analysis = self.analyze_by_category()
        report.append(cat_analysis.to_string())

        # Top suppliers
        report.append("\n## TOP SUPPLIERS BY VALUE")
        supplier_analysis = self.analyze_by_supplier()
        report.append(supplier_analysis.head(10).to_string())

        # High value items
        report.append("\n## HIGH VALUE ITEMS")
        high_value = self.identify_high_value_items()
        report.append(high_value.to_string())

        # Stock status
        report.append("\n## STOCK STATUS BY CATEGORY")
        stock_status = self.analyze_stock_status()
        for category, status in stock_status.items():
            report.append(f"\n{category}:")
            report.append(f"  - In Stock: {status['in_stock']} items")
            report.append(f"  - Out of Stock: {status['out_of_stock']} items")
            report.append(f"  - Stock Rate: {status['percentage_stocked']}%")

        return "\n".join(report)

    def plot_category_distribution(self, save_path: str = None):
        """Create a pie chart of product distribution by category."""
        plt.figure(figsize=(10, 8))
        category_counts = self.df['category'].value_counts()

        plt.pie(category_counts.values, labels=category_counts.index, autopct='%1.1f%%')
        plt.title('Product Distribution by Category')

        if save_path:
            plt.savefig(save_path)
        plt.close()

    def plot_supplier_values(self, top_n: int = 10, save_path: str = None):
        """Create a bar chart of top suppliers by total value."""
        plt.figure(figsize=(12, 6))
        supplier_values = self.df.groupby('supplier')['price'].sum().sort_values(ascending=False).head(top_n)

        plt.bar(range(len(supplier_values)), supplier_values.values)
        plt.xticks(range(len(supplier_values)), supplier_values.index, rotation=45, ha='right')
        plt.xlabel('Supplier')
        plt.ylabel('Total Value (€)')
        plt.title(f'Top {top_n} Suppliers by Total Inventory Value')
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path)
        plt.close()

    def export_analysis(self, output_dir: str = '.'):
        """Export complete analysis with visualizations."""
        # Generate report
        report = self.generate_report()
        with open(f"{output_dir}/inventory_report.txt", 'w', encoding='utf-8') as f:
            f.write(report)

        # Generate visualizations
        self.plot_category_distribution(f"{output_dir}/category_distribution.png")
        self.plot_supplier_values(save_path=f"{output_dir}/top_suppliers.png")

        # Export detailed data
        self.df.to_csv(f"{output_dir}/inventory_cleaned.csv", index=False)
        self.analyze_by_category().to_csv(f"{output_dir}/category_analysis.csv")
        self.analyze_by_supplier().to_csv(f"{output_dir}/supplier_analysis.csv")

        print(f"Analysis exported to {output_dir}/")


# Example usage
if __name__ == "__main__":
    # Sample data string (paste your data here)
    data_string = """0	ACQDIREZIONE	ACQUISTI DIREZIONE	PROPDIRE	PROPDIRE	PZ	BELLAGAIA SRL	0	0.0 PZ	284.9	0	0	0	0	0 PZ/g	0 PZ/g	0 PZ/g	0 PZ/g	0	0.00 PZ/giorno	0	0.0 PZ
1	ACQNETTO	ACQUISTO SUPERMERCATO NETTO	PROPDIRE	PROPDIRE	PZ	AMALFI SEI ESSE SRL	0	0.0 PZ	13.61	0	0	0	0	0 PZ/g	0 PZ/g	0 PZ/g	0 PZ/g	0	0.00 PZ/giorno	0	0.0 PZ
2	ATT.AHK.00001	FILO STENDIBIANCHERIA MM5	ATTREZZ	AT.HSK	MT	GIACINTO DI PALMA	0	0.0 MT	0.492	0	0	0	0	0 MT/g	0 MT/g	0 MT/g	0 MT/g	0	0.00 MT/giorno	0	0.0 MT
3	ATT.ASB.00001	PORTA GHIACCIO	ATTREZZ	AT.SALA	PZ	CARICO INIZIALE	0	0.0 PZ	0	0	0	0	0	0 PZ/g	0 PZ/g	0 PZ/g	0 PZ/g	0	0.00 PZ/giorno	0	0.0 PZ
4	ATT.ASB.00002	PINZA PLASTICA PER GHIACCIO	ATTREZZ	AT.SALA	PZ	CARICO INIZIALE	0	0.0 PZ	0	0	0	0	0	0 PZ/g	0 PZ/g	0 PZ/g	0 PZ/g	0	0.00 PZ/giorno	0	0.0 PZ
5	ATT.ATB.00001	TAPPETO PER SPIAGGIA VERDE 110X55M	ATTREZZ	AT.SPIAG	PZ	BRASIO MIRKO VINCENZO	0	0.0 PZ	287.1	0	0	0	0	0 PZ/g	0 PZ/g	0 PZ/g	0 PZ/g	0	0.00 PZ/giorno	0	0.0 PZ
6	ATT.ATC.00001	TEGLIA DA FORNO CIRCOLARE 26CM	ATTREZZ	AT.CUCIN	PZ	AMAZON	6	6.0 PZ	9.41	0	0	0	0	0 PZ/g	0 PZ/g	0 PZ/g	0 PZ/g	0	0.00 PZ/giorno	0	0.0 PZ
7	ATT.ATC.00002	VENTILATORE	ATTREZZ	AT.CAMER	PZ	NINNI SRL	0	0.0 PZ	0	0	0	0	0	0 PZ/g	0 PZ/g	0 PZ/g	0 PZ/g	0	0.00 PZ/giorno	0	0.0 PZ
8	ATT.ATC.00003	SACCAPOCHE 100PZ	ATTREZZ	AT.CUCIN	CF	VICART SRL	4	4.0 CF	22	0	0	0	0	0 CF/g	0 CF/g	0 CF/g	0 CF/g	0	0.00 CF/giorno	0	0.0 CF
9	ATT.ATC.00004	BADGE CAMERE VDA	ATTREZZ	AT.CAMER	PZ	VDA GROUP SPA	100	100.0 PZ	0.9	0	0	0	0	0 PZ/g	0 PZ/g	0 PZ/g	0 PZ/g	0	0.00 PZ/giorno	0	0.0 PZ
10	ATT.ATE.00001	CARICATORE USB 6 PORTE	ATTREZZ	AT.TELEF	PZ	AMAZON	1	1.0 PZ	22.36	0	0	0	0	0 PZ/g	0 PZ/g	0 PZ/g	0 PZ/g	0	0.00 PZ/giorno	0	0.0 PZ
11	ATT.ATE.00002	CARICATORE IPHONE	ATTREZZ	AT.TELEF	PZ	AMAZON	1	1.0 PZ	12.14	0	0	0	0	0 PZ/g	0 PZ/g	0 PZ/g	0 PZ/g	0	0.00 PZ/giorno	0	0.0 PZ
12	ATT.ATH.00001	LAVASCIUGA I-MOP LITE COMPLETO	ATTREZZ	AT.HSK	PZ	FORAGGIO SRL	0	0.0 PZ	0	0	0	0	0	0 PZ/g	0 PZ/g	0 PZ/g	0 PZ/g	0	0.00 PZ/giorno	0	0.0 PZ
13	ATT.ATH.00002	KIT DISCO PER I-MOP LITE BLU 1CFX2PZ	ATTREZZ	AT.HSK	PZ	FORAGGIO SRL	0	0.0 PZ	0	0	0	0	0	0 PZ/g	0 PZ/g	0 PZ/g	0 PZ/g	0	0.00 PZ/giorno	0	0.0 PZ
14	ATT.ATH.00003	LAVASCIUGA I-MOP XL PRO	ATTREZZ	AT.HSK	PZ	FORAGGIO SRL	0	0.0 PZ	0	0	0	0	0	0 PZ/g	0 PZ/g	0 PZ/g	0 PZ/g	0	0.00 PZ/giorno	0	0.0 PZ
15	ATT.ATH.00004	BATTERIA POWER14 DESTRA PER I-MOP	ATTREZZ	AT.HSK	PZ	FORAGGIO SRL	0	0.0 PZ	0	0	0	0	0	0 PZ/g	0 PZ/g	0 PZ/g	0 PZ/g	0	0.00 PZ/giorno	0	0.0 PZ
16	ATT.ATH.00005	CARICABATTERIA SUPER 3P EU	ATTREZZ	AT.HSK	PZ	FORAGGIO SRL	0	0.0 PZ	0	0	0	0	0	0 PZ/g	0 PZ/g	0 PZ/g	0 PZ/g	0	0.00 PZ/giorno	0	0.0 PZ
17	ATT.ATH.00006	DISCO SINGOLO PER I-MOP	ATTREZZ	AT.HSK	PZ	FORAGGIO SRL	0	0.0 PZ	0	0	0	0	0	0 PZ/g	0 PZ/g	0 PZ/g	0 PZ/g	0	0.00 PZ/giorno	0	0.0 PZ
18	ATT.ATH.00007	DISCO ABRASIVO ROSSO I-MOP XL	ATTREZZ	AT.HSK	PZ	FORAGGIO SRL	0	0.0 PZ	0	0	0	0	0	0 PZ/g	0 PZ/g	0 PZ/g	0 PZ/g	0	0.00 PZ/giorno	0	0.0 PZ
19	ATT.ATH.00008	ICLEAN PRO TERSANO	ATTREZZ	AT.HSK	PZ	FORAGGIO SRL	0	0.0 PZ	0	0	0	0	0	0 PZ/g	0 PZ/g	0 PZ/g	0 PZ/g	0	0.00 PZ/giorno	0	0.0 PZ"""

    # Initialize analyzer
    analyzer = InventoryAnalyzer()

    # Load data
    analyzer.load_data(data_string)

    # Generate and print report
    print(analyzer.generate_report())

    # Export complete analysis
    analyzer.export_analysis("./data_analysis")
