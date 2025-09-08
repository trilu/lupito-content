#!/usr/bin/env python3
"""
Base connector class for all retailer integrations
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
import logging
import time
from datetime import datetime
import os
import yaml
import json
from supabase import create_client, Client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RetailerConnector(ABC):
    """Abstract base class for retailer connectors"""
    
    def __init__(self, retailer_name: str, config_path: str = None):
        """
        Initialize connector with retailer configuration
        
        Args:
            retailer_name: Name of retailer (must match config)
            config_path: Path to retailers.yaml config file
        """
        self.retailer_name = retailer_name
        self.config = self._load_config(config_path)
        self.retailer_config = self.config['retailers'].get(retailer_name)
        
        if not self.retailer_config:
            raise ValueError(f"No configuration found for retailer: {retailer_name}")
        
        # Initialize Supabase client
        self.supabase = self._init_supabase()
        
        # Track rate limiting
        self.last_request_time = 0
        self.request_count = 0
        
        # Statistics
        self.stats = {
            'products_found': 0,
            'products_saved': 0,
            'errors': 0,
            'start_time': datetime.utcnow()
        }
    
    def _load_config(self, config_path: str = None) -> Dict:
        """Load retailer configuration from YAML file"""
        if not config_path:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'config', 'retailers.yaml'
            )
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _init_supabase(self) -> Client:
        """Initialize Supabase client"""
        supabase_url = os.environ.get('SUPABASE_URL', 'https://cibjeqgftuxuezarjsdl.supabase.co')
        supabase_key = os.environ.get('SUPABASE_KEY')
        
        if not supabase_key:
            raise ValueError("SUPABASE_KEY environment variable must be set")
        
        return create_client(supabase_url, supabase_key)
    
    def rate_limit(self):
        """Implement rate limiting based on config"""
        if 'rate_limit' not in self.retailer_config.get('api', {}):
            return
        
        rate_config = self.retailer_config['api']['rate_limit']
        max_rps = rate_config.get('requests_per_second', 10)
        
        # Calculate minimum time between requests
        min_interval = 1.0 / max_rps
        
        # Wait if necessary
        elapsed = time.time() - self.last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    @abstractmethod
    def search_brand(self, brand_name: str, page: int = 1) -> List[Dict]:
        """
        Search for products by brand name
        
        Args:
            brand_name: Brand to search for
            page: Page number for pagination
            
        Returns:
            List of product dictionaries
        """
        pass
    
    @abstractmethod
    def get_product_details(self, product_id: str) -> Optional[Dict]:
        """
        Get detailed information for a single product
        
        Args:
            product_id: Retailer's product ID
            
        Returns:
            Product dictionary with all details
        """
        pass
    
    @abstractmethod
    def parse_nutrition(self, product_data: Dict) -> Dict:
        """
        Extract and parse nutrition information
        
        Args:
            product_data: Raw product data from retailer
            
        Returns:
            Standardized nutrition dictionary
        """
        pass
    
    def normalize_product(self, raw_product: Dict) -> Dict:
        """
        Normalize product data to match database schema
        
        Args:
            raw_product: Raw product data from retailer
            
        Returns:
            Normalized product dictionary
        """
        # Map retailer fields to database fields
        field_map = self.retailer_config.get('fields', {})
        
        normalized = {
            'retailer_source': self.retailer_name,
            'data_source': 'api' if self.retailer_config['type'] != 'scraper_only' else 'scraper',
            'last_api_sync': datetime.utcnow().isoformat(),
            'api_response': json.dumps(raw_product)  # Store raw response
        }
        
        # Map fields using configuration
        for db_field, retailer_field in field_map.items():
            value = self._extract_nested_field(raw_product, retailer_field)
            if value is not None:
                # Map to correct database column names
                if db_field == 'product_name':
                    normalized['product_name'] = value
                elif db_field == 'brand':
                    normalized['brand'] = value
                elif db_field == 'price':
                    normalized['retailer_price_eur'] = float(value) if value else None
                elif db_field == 'ingredients':
                    normalized['ingredients_raw'] = value
                elif db_field == 'protein':
                    normalized['protein_percent'] = self._parse_percentage(value)
                elif db_field == 'fat':
                    normalized['fat_percent'] = self._parse_percentage(value)
                elif db_field == 'fiber':
                    normalized['fiber_percent'] = self._parse_percentage(value)
                elif db_field == 'ash':
                    normalized['ash_percent'] = self._parse_percentage(value)
                elif db_field == 'moisture':
                    normalized['moisture_percent'] = self._parse_percentage(value)
                elif db_field == 'images':
                    normalized['image_urls'] = value if isinstance(value, list) else [value]
                    normalized['image_primary_url'] = value[0] if isinstance(value, list) and value else value
                elif db_field == 'in_stock':
                    normalized['retailer_in_stock'] = bool(value)
                elif db_field == 'rating':
                    normalized['retailer_rating'] = float(value) if value else None
                elif db_field == 'reviews':
                    normalized['retailer_review_count'] = int(value) if value else None
        
        # Add nutrition data
        nutrition = self.parse_nutrition(raw_product)
        normalized.update(nutrition)
        
        return normalized
    
    def _extract_nested_field(self, data: Dict, field_path: str) -> Any:
        """
        Extract nested field from dictionary using dot notation
        
        Args:
            data: Dictionary to extract from
            field_path: Path like "brand.name" or "images[].url"
            
        Returns:
            Extracted value or None
        """
        if not data or not field_path:
            return None
        
        # Handle array notation
        if '[]' in field_path:
            base_path, array_field = field_path.split('[].')
            base_value = self._extract_nested_field(data, base_path)
            if isinstance(base_value, list):
                return [item.get(array_field) for item in base_value if isinstance(item, dict)]
            return None
        
        # Handle dot notation
        parts = field_path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        
        return current
    
    def _parse_percentage(self, value: Any) -> Optional[float]:
        """Parse percentage value from various formats"""
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # Remove % sign and parse
            value = value.replace('%', '').replace(',', '.').strip()
            try:
                return float(value)
            except ValueError:
                return None
        
        return None
    
    def validate_product(self, product: Dict) -> bool:
        """
        Validate that product has required fields
        
        Args:
            product: Normalized product dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['brand', 'product_name']
        
        for field in required_fields:
            if not product.get(field):
                logger.warning(f"Product missing required field: {field}")
                return False
        
        # Validate nutrition data ranges
        nutrition_fields = ['protein_percent', 'fat_percent', 'fiber_percent', 'ash_percent', 'moisture_percent']
        for field in nutrition_fields:
            value = product.get(field)
            if value is not None:
                if value < 0 or value > 100:
                    logger.warning(f"Invalid {field}: {value}")
                    return False
        
        return True
    
    def save_products(self, products: List[Dict]) -> int:
        """
        Save products to database
        
        Args:
            products: List of normalized product dictionaries
            
        Returns:
            Number of products saved
        """
        if not products:
            return 0
        
        saved_count = 0
        batch_size = self.config['global'].get('batch_size', 100)
        
        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            
            try:
                # Upsert products (update if exists, insert if new)
                response = self.supabase.table('food_candidates_sc').upsert(
                    batch,
                    on_conflict='brand,product_name,retailer_source'
                ).execute()
                
                saved_count += len(batch)
                logger.info(f"Saved batch of {len(batch)} products")
                
            except Exception as e:
                logger.error(f"Error saving batch: {e}")
                self.stats['errors'] += 1
                
                # Try saving individually
                for product in batch:
                    try:
                        self.supabase.table('food_candidates_sc').upsert(product).execute()
                        saved_count += 1
                    except Exception as individual_error:
                        logger.error(f"Error saving product {product.get('product_name')}: {individual_error}")
                        self.stats['errors'] += 1
        
        self.stats['products_saved'] += saved_count
        return saved_count
    
    def sync_brand(self, brand_name: str) -> Dict:
        """
        Sync all products for a brand
        
        Args:
            brand_name: Brand to sync
            
        Returns:
            Statistics dictionary
        """
        logger.info(f"Syncing brand: {brand_name}")
        all_products = []
        page = 1
        
        while True:
            # Search for products
            products = self.search_brand(brand_name, page)
            
            if not products:
                break
            
            # Get detailed information for each product
            detailed_products = []
            for product in products:
                product_id = product.get('id') or product.get('product_id')
                if product_id:
                    details = self.get_product_details(product_id)
                    if details:
                        normalized = self.normalize_product(details)
                        if self.validate_product(normalized):
                            detailed_products.append(normalized)
                            self.stats['products_found'] += 1
            
            all_products.extend(detailed_products)
            
            # Check if there are more pages
            if len(products) < 100:  # Assuming 100 products per page
                break
            
            page += 1
        
        # Save all products
        if all_products:
            self.save_products(all_products)
        
        logger.info(f"Completed sync for {brand_name}: {len(all_products)} products")
        return self.get_statistics()
    
    def sync_all_brands(self, brands: List[str]) -> Dict:
        """
        Sync all brands from list
        
        Args:
            brands: List of brand names to sync
            
        Returns:
            Overall statistics
        """
        logger.info(f"Starting sync for {len(brands)} brands")
        
        for brand in brands:
            try:
                self.sync_brand(brand)
            except Exception as e:
                logger.error(f"Error syncing brand {brand}: {e}")
                self.stats['errors'] += 1
        
        return self.get_statistics()
    
    def get_statistics(self) -> Dict:
        """Get current statistics"""
        elapsed = (datetime.utcnow() - self.stats['start_time']).total_seconds()
        
        return {
            'retailer': self.retailer_name,
            'products_found': self.stats['products_found'],
            'products_saved': self.stats['products_saved'],
            'errors': self.stats['errors'],
            'elapsed_seconds': elapsed,
            'products_per_minute': (self.stats['products_saved'] / elapsed * 60) if elapsed > 0 else 0
        }