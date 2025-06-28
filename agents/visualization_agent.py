"""
Visualization Agent for creating charts and graphs from query results
"""
import json
import base64
from io import BytesIO
from typing import Dict, Any, List, Optional, Tuple
from .base_agent import BaseAgent

# Import visualization libraries (with fallbacks)
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.utils import PlotlyJSONEncoder
    import pandas as pd
    import numpy as np
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    # Create placeholder classes
    class plt:
        @staticmethod
        def figure(): pass
        @staticmethod
        def savefig(*args, **kwargs): pass
        @staticmethod
        def close(): pass

class VisualizationAgent(BaseAgent):
    """Agent specialized in creating visualizations from data"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("VisualizationAgent", config)
        
        # Visualization settings
        self.default_chart_type = config.get("default_chart_type", "auto")
        self.max_categories = config.get("max_categories", 20)
        self.figure_size = config.get("figure_size", (10, 6))
        self.color_palette = config.get("color_palette", "viridis")
        self.export_formats = config.get("export_formats", ["png", "json", "html"])
        
        # Chart type mappings
        self.chart_type_mappings = {
            "bar": ["count", "total", "sum", "comparison"],
            "line": ["trend", "time", "date", "over_time"],
            "pie": ["distribution", "percentage", "breakdown"],
            "scatter": ["correlation", "relationship"],
            "heatmap": ["matrix", "correlation_matrix"],
            "histogram": ["frequency", "distribution"]
        }
        
        # Color schemes
        self.color_schemes = {
            "police": ["#1f4e79", "#2d5aa0", "#4472c4", "#8fa2d1"],
            "status": ["#28a745", "#ffc107", "#dc3545", "#6c757d"],
            "districts": ["#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"],
            "default": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
        }
        
        if not VISUALIZATION_AVAILABLE:
            self.logger.warning("⚠️ Visualization libraries not available. Install matplotlib, seaborn, plotly, pandas")
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create visualizations from data"""
        
        if not VISUALIZATION_AVAILABLE:
            return {
                "success": False,
                "error": "Visualization libraries not installed",
                "suggestion": "Install: pip install matplotlib seaborn plotly pandas"
            }
        
        viz_type = input_data.get("type", "auto_chart")
        
        if viz_type == "auto_chart":
            return await self._create_auto_chart(input_data)
        elif viz_type == "specific_chart":
            return await self._create_specific_chart(input_data)
        elif viz_type == "dashboard":
            return await self._create_dashboard(input_data)
        elif viz_type == "export_chart":
            return await self._export_existing_chart(input_data)
        else:
            raise ValueError(f"Unsupported visualization type: {viz_type}")
    
    async def _validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate visualization input"""
        base_validation = await super()._validate_input(input_data)
        if not base_validation["valid"]:
            return base_validation
        
        data = input_data.get("data", [])
        if not data:
            return {"valid": False, "reason": "Data is required for visualization"}
        
        if not isinstance(data, list):
            return {"valid": False, "reason": "Data must be a list of dictionaries"}
        
        if data and not isinstance(data[0], dict):
            return {"valid": False, "reason": "Data must be a list of dictionaries"}
        
        return {"valid": True}
    
    async def _create_auto_chart(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Automatically determine and create the best chart type"""
        
        data = input_data.get("data", [])
        title = input_data.get("title", "Auto-Generated Chart")
        
        self.logger.info(f"📊 Creating auto chart for {len(data)} data points")
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            if df.empty:
                return {"success": False, "error": "No data to visualize"}
            
            # Analyze data to determine best chart type
            chart_recommendation = await self._analyze_data_for_chart_type(df)
            
            # Create the recommended chart
            chart_result = await self._create_chart_by_type(
                df, 
                chart_recommendation["chart_type"],
                title,
                chart_recommendation["config"]
            )
            
            return {
                "success": True,
                "chart_type": chart_recommendation["chart_type"],
                "recommendation_reason": chart_recommendation["reason"],
                "charts": chart_result["charts"],
                "data_summary": await self._generate_data_summary(df),
                "context_updates": {
                    "last_chart_type": chart_recommendation["chart_type"],
                    "last_data_points": len(data)
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Auto chart creation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "data_summary": f"Failed to process {len(data)} data points"
            }
    
    async def _create_specific_chart(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a specific type of chart"""
        
        data = input_data.get("data", [])
        chart_type = input_data.get("chart_type", "bar")
        title = input_data.get("title", f"{chart_type.title()} Chart")
        config = input_data.get("config", {})
        
        self.logger.info(f"📈 Creating {chart_type} chart")
        
        try:
            df = pd.DataFrame(data)
            
            chart_result = await self._create_chart_by_type(df, chart_type, title, config)
            
            return {
                "success": True,
                "chart_type": chart_type,
                "charts": chart_result["charts"],
                "data_summary": await self._generate_data_summary(df)
            }
            
        except Exception as e:
            self.logger.error(f"❌ {chart_type} chart creation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "chart_type": chart_type
            }
    
    async def _create_dashboard(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a dashboard with multiple charts"""
        
        datasets = input_data.get("datasets", [])
        dashboard_title = input_data.get("title", "CCTNS Dashboard")
        
        if not datasets:
            return {"success": False, "error": "No datasets provided for dashboard"}
        
        self.logger.info(f"🎛️ Creating dashboard with {len(datasets)} charts")
        
        try:
            dashboard_charts = []
            
            for i, dataset in enumerate(datasets):
                chart_result = await self._create_auto_chart({
                    **dataset,
                    "title": dataset.get("title", f"Chart {i+1}")
                })
                
                if chart_result["success"]:
                    dashboard_charts.extend(chart_result["charts"])
            
            # Create combined dashboard HTML
            dashboard_html = await self._create_dashboard_html(dashboard_charts, dashboard_title)
            
            return {
                "success": True,
                "dashboard_title": dashboard_title,
                "total_charts": len(dashboard_charts),
                "charts": dashboard_charts,
                "dashboard_html": dashboard_html
            }
            
        except Exception as e:
            self.logger.error(f"❌ Dashboard creation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _analyze_data_for_chart_type(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze DataFrame to recommend best chart type"""
        
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
        
        num_rows = len(df)
        num_numeric = len(num_cols)
        num_categorical = len(cat_cols)
        
        # Decision logic for chart type
        if date_cols and num_numeric > 0:
            return {
                "chart_type": "line",
                "reason": "Time series data detected",
                "config": {"x_col": date_cols[0], "y_col": num_cols[0]}
            }
        
        elif num_categorical == 1 and num_numeric == 1:
            unique_categories = df[cat_cols[0]].nunique()
            
            if unique_categories <= 10:
                if unique_categories <= 5:
                    return {
                        "chart_type": "pie",
                        "reason": "Few categories suitable for pie chart",
                        "config": {"category_col": cat_cols[0], "value_col": num_cols[0]}
                    }
                else:
                    return {
                        "chart_type": "bar",
                        "reason": "Categorical data with numeric values",
                        "config": {"x_col": cat_cols[0], "y_col": num_cols[0]}
                    }
            else:
                return {
                    "chart_type": "bar",
                    "reason": "Many categories, bar chart recommended",
                    "config": {"x_col": cat_cols[0], "y_col": num_cols[0]}
                }
        
        elif num_numeric >= 2:
            return {
                "chart_type": "scatter",
                "reason": "Multiple numeric columns for correlation analysis",
                "config": {"x_col": num_cols[0], "y_col": num_cols[1]}
            }
        
        elif num_categorical >= 1:
            return {
                "chart_type": "bar",
                "reason": "Categorical data for frequency analysis",
                "config": {"x_col": cat_cols[0], "y_col": "count"}
            }
        
        else:
            return {
                "chart_type": "bar",
                "reason": "Default chart type",
                "config": {}
            }
    
    async def _create_chart_by_type(self, df: pd.DataFrame, chart_type: str, title: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create chart based on specified type"""
        
        charts = []
        
        if chart_type == "bar":
            charts.extend(await self._create_bar_chart(df, title, config))
        elif chart_type == "line":
            charts.extend(await self._create_line_chart(df, title, config))
        elif chart_type == "pie":
            charts.extend(await self._create_pie_chart(df, title, config))
        elif chart_type == "scatter":
            charts.extend(await self._create_scatter_chart(df, title, config))
        elif chart_type == "heatmap":
            charts.extend(await self._create_heatmap(df, title, config))
        elif chart_type == "histogram":
            charts.extend(await self._create_histogram(df, title, config))
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")
        
        return {"charts": charts}
    
    async def _create_bar_chart(self, df: pd.DataFrame, title: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create bar chart"""
        charts = []
        
        # Determine x and y columns
        x_col = config.get("x_col")
        y_col = config.get("y_col")
        
        if not x_col or not y_col:
            # Auto-determine columns
            cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            
            if cat_cols and num_cols:
                x_col = cat_cols[0]
                y_col = num_cols[0]
            elif cat_cols:
                x_col = cat_cols[0]
                y_col = "count"
                df = df.groupby(x_col).size().reset_index(name='count')
            else:
                raise ValueError("No suitable columns for bar chart")
        
        # Limit categories if too many
        if df[x_col].nunique() > self.max_categories:
            top_categories = df.nlargest(self.max_categories, y_col)
            df = top_categories
        
        # Create Plotly bar chart
        fig = px.bar(
            df, 
            x=x_col, 
            y=y_col,
            title=title,
            color_discrete_sequence=self.color_schemes["default"]
        )
        
        fig.update_layout(
            xaxis_title=x_col.replace('_', ' ').title(),
            yaxis_title=y_col.replace('_', ' ').title(),
            showlegend=False
        )
        
        # Convert to formats
        charts.append({
            "format": "plotly_json",
            "data": fig.to_json(),
            "chart_type": "bar",
            "title": title
        })
        
        charts.append({
            "format": "html",
            "data": fig.to_html(include_plotlyjs=True),
            "chart_type": "bar",
            "title": title
        })
        
        return charts
    
    async def _create_line_chart(self, df: pd.DataFrame, title: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create line chart"""
        charts = []
        
        x_col = config.get("x_col")
        y_col = config.get("y_col")
        
        if not x_col or not y_col:
            # Auto-determine columns
            date_cols = [col for col in df.columns if 'date' in col.lower()]
            num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            
            if date_cols and num_cols:
                x_col = date_cols[0]
                y_col = num_cols[0]
            else:
                raise ValueError("No suitable columns for line chart")
        
        # Sort by x column for proper line chart
        df = df.sort_values(x_col)
        
        fig = px.line(
            df,
            x=x_col,
            y=y_col,
            title=title,
            color_discrete_sequence=self.color_schemes["police"]
        )
        
        fig.update_layout(
            xaxis_title=x_col.replace('_', ' ').title(),
            yaxis_title=y_col.replace('_', ' ').title()
        )
        
        charts.append({
            "format": "plotly_json",
            "data": fig.to_json(),
            "chart_type": "line",
            "title": title
        })
        
        charts.append({
            "format": "html", 
            "data": fig.to_html(include_plotlyjs=True),
            "chart_type": "line",
            "title": title
        })
        
        return charts
    
    async def _create_pie_chart(self, df: pd.DataFrame, title: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create pie chart"""
        charts = []
        
        category_col = config.get("category_col")
        value_col = config.get("value_col")
        
        if not category_col:
            cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            if cat_cols:
                category_col = cat_cols[0]
            else:
                raise ValueError("No categorical column for pie chart")
        
        if not value_col:
            num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if num_cols:
                value_col = num_cols[0]
            else:
                # Count occurrences
                value_col = "count"
                df = df.groupby(category_col).size().reset_index(name='count')
        
        # Limit slices
        if df[category_col].nunique() > 10:
            top_data = df.nlargest(10, value_col)
            others_sum = df[~df[category_col].isin(top_data[category_col])][value_col].sum()
            if others_sum > 0:
                others_row = pd.DataFrame({category_col: ['Others'], value_col: [others_sum]})
                df = pd.concat([top_data, others_row], ignore_index=True)
        
        fig = px.pie(
            df,
            values=value_col,
            names=category_col,
            title=title,
            color_discrete_sequence=self.color_schemes["districts"]
        )
        
        charts.append({
            "format": "plotly_json",
            "data": fig.to_json(),
            "chart_type": "pie",
            "title": title
        })
        
        charts.append({
            "format": "html",
            "data": fig.to_html(include_plotlyjs=True),
            "chart_type": "pie", 
            "title": title
        })
        
        return charts
    
    async def _create_scatter_chart(self, df: pd.DataFrame, title: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create scatter plot"""
        charts = []
        
        x_col = config.get("x_col")
        y_col = config.get("y_col")
        
        if not x_col or not y_col:
            num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if len(num_cols) >= 2:
                x_col = num_cols[0]
                y_col = num_cols[1]
            else:
                raise ValueError("Need at least 2 numeric columns for scatter plot")
        
        fig = px.scatter(
            df,
            x=x_col,
            y=y_col,
            title=title,
            color_discrete_sequence=self.color_schemes["default"]
        )
        
        fig.update_layout(
            xaxis_title=x_col.replace('_', ' ').title(),
            yaxis_title=y_col.replace('_', ' ').title()
        )
        
        charts.append({
            "format": "plotly_json",
            "data": fig.to_json(),
            "chart_type": "scatter",
            "title": title
        })
        
        return charts
    
    async def _create_heatmap(self, df: pd.DataFrame, title: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create heatmap"""
        charts = []
        
        # Create correlation matrix for numeric columns
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(num_cols) < 2:
            raise ValueError("Need at least 2 numeric columns for heatmap")
        
        correlation_matrix = df[num_cols].corr()
        
        fig = px.imshow(
            correlation_matrix,
            title=f"{title} - Correlation Matrix",
            color_continuous_scale="RdBu_r",
            aspect="auto"
        )
        
        charts.append({
            "format": "plotly_json",
            "data": fig.to_json(),
            "chart_type": "heatmap",
            "title": title
        })
        
        return charts
    
    async def _create_histogram(self, df: pd.DataFrame, title: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create histogram"""
        charts = []
        
        column = config.get("column")
        
        if not column:
            num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if num_cols:
                column = num_cols[0]
            else:
                raise ValueError("No numeric column for histogram")
        
        fig = px.histogram(
            df,
            x=column,
            title=title,
            color_discrete_sequence=self.color_schemes["police"]
        )
        
        fig.update_layout(
            xaxis_title=column.replace('_', ' ').title(),
            yaxis_title="Frequency"
        )
        
        charts.append({
            "format": "plotly_json",
            "data": fig.to_json(),
            "chart_type": "histogram",
            "title": title
        })
        
        return charts
    
    async def _generate_data_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate summary of the data"""
        
        return {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "column_types": {
                "numeric": len(df.select_dtypes(include=[np.number]).columns),
                "categorical": len(df.select_dtypes(include=['object', 'category']).columns),
                "datetime": len(df.select_dtypes(include=['datetime']).columns)
            },
            "missing_values": df.isnull().sum().to_dict(),
            "memory_usage": f"{df.memory_usage(deep=True).sum() / 1024:.2f} KB"
        }
    
    async def _create_dashboard_html(self, charts: List[Dict[str, Any]], title: str) -> str:
        """Create combined dashboard HTML"""
        
        html_charts = [chart for chart in charts if chart["format"] == "html"]
        
        dashboard_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .dashboard-header {{ text-align: center; margin-bottom: 30px; }}
                .chart-container {{ margin-bottom: 40px; }}
                .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 20px; }}
            </style>
        </head>
        <body>
            <div class="dashboard-header">
                <h1>{title}</h1>
                <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <div class="grid">
        """
        
        for chart in html_charts:
            dashboard_html += f"""
                <div class="chart-container">
                    {chart['data']}
                </div>
            """
        
        dashboard_html += """
            </div>
        </body>
        </html>
        """
        
        return dashboard_html
    
    async def get_available_chart_types(self) -> List[str]:
        """Get list of available chart types"""
        return list(self.chart_type_mappings.keys())
    
    async def get_visualization_stats(self) -> Dict[str, Any]:
        """Get visualization statistics"""
        return {
            "agent_stats": self.get_status(),
            "visualization_specific": {
                "available_chart_types": await self.get_available_chart_types(),
                "libraries_available": VISUALIZATION_AVAILABLE,
                "max_categories": self.max_categories,
                "export_formats": self.export_formats,
                "color_schemes": list(self.color_schemes.keys())
            }
        }
