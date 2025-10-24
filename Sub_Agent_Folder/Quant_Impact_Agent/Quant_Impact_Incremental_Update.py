"""
Quant Impact Incremental Update Agent - Complete Pipeline

This module implements intelligent incremental updates for Quant Impact Analysis:
1. Checks if ticker exists in database
2. If not exists: Calls Quant_Impact_DB_Agent to generate 8 datasets
3. If exists: Calls Quant_Impact_Update_Metrics to get new metrics from previous update to today
4. Uses LLM-based factor mapping to merge old and new metrics
5. Generates all 8 datasets using Storage Agent pipeline
6. Replaces old 8 datasets in Redis with updated ones

Author: Assistant
Date: 2025-01-03
Version: 2.0 (ACTIVE)
"""

import redis
import json
import pandas as pd
import numpy as np
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from io import StringIO
import sys
import os
from pathlib import Path

# Add project root to path
ROOT_SENTINEL = "LLM_Call_Agent.py"
def find_repo_root(start: Path) -> Path:
    for path in (start, *start.parents):
        if (path / ROOT_SENTINEL).exists():
            return path
    raise FileNotFoundError(f"Could not locate {ROOT_SENTINEL} upward from {start}")

repo_root = find_repo_root(Path.cwd())
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Import existing components
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from LLM_Call_Agent import LLMCallAgent
from Quant_Impact_Agent.Quant_Impact_DB_Agent import QuantImpactDBAgent
from Quant_Impact_Agent.Quant_Impact_Update_Metrics import generate_update_metrics
from Quant_Impact_Agent.Quant_Impact_Storage_Agent import (
    quant_impact_risk_analysis, generate_impact_summary_schema, 
    convert_schema_to_compound_datasets, QuantImpactStorageAgent
)
from shared_clients import shared_clients

# Redis Configuration
REDIS_HOST = "redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com"
REDIS_PORT = 16376
REDIS_USERNAME = "default"
REDIS_PASSWORD = "rl8242B4UItBhFzgHW5APEqZnkYoaEZv"

class QuantImpactIncrementalUpdate:
    """
    Complete Incremental Update Agent for Quant Impact Analysis
    
    Features:
    1. Checks if ticker exists in database
    2. If not exists: Calls Quant_Impact_DB_Agent to generate 8 datasets
    3. If exists: Calls Quant_Impact_Update_Metrics + LLM merging
    4. Generates all 8 datasets using Storage Agent pipeline
    5. Replaces old 8 datasets in Redis with updated ones
    """
    
    def __init__(self, shared_clients=None):
        """
        Initialize the Incremental Update Agent
        
        Args:
            shared_clients: Shared clients for LLM operations
        """
        self.shared_clients = shared_clients
        
        # Initialize shared clients (will be set during execution if None)
        # No initialization needed here - will use shared_clients parameter
        
        # Redis client for data operations
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            username=REDIS_USERNAME,
            password=REDIS_PASSWORD,
            decode_responses=True,
        )
        
        # Initialize DB Agent
        self.db_agent = QuantImpactDBAgent(shared_clients=self.shared_clients)
        
        # Initialize Storage Agent
        self.storage_agent = QuantImpactStorageAgent(shared_clients=self.shared_clients)
        
    def debug_check_datasets_complete(self, ticker: str) -> bool:
        """
        Debug function to check if all 8 datasets exist and are valid
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            True if all 8 datasets exist and are valid, False otherwise
        """
        print(f"🔍 DEBUG: Checking dataset completeness for {ticker}")
        print("=" * 60)
        
        try:
            # Retrieve datasets from Redis
            datasets = self.db_agent.retrieve_datasets(ticker)
            
            if datasets.get("status") != "success":
                print(f"❌ Failed to retrieve datasets: {datasets.get('error', 'Unknown error')}")
                return False
            
            # Required 8 datasets
            required_datasets = [
                'risk_share_index',
                'macro_volatility_df', 
                'micro_volatility_df',
                'impact_metrics_df',
                'macro_total_impact_df',
                'micro_total_impact_df',
                'Factor_Risk_Reward',
                'factor_time_df'
            ]
            
            missing_datasets = []
            empty_datasets = []
            
            for dataset_name in required_datasets:
                if dataset_name not in datasets:
                    missing_datasets.append(dataset_name)
                    print(f"❌ Missing: {dataset_name}")
                else:
                    dataset_value = datasets[dataset_name]
                    
                    # Check if DataFrame is empty or None
                    if hasattr(dataset_value, 'empty'):
                        if dataset_value.empty:
                            empty_datasets.append(dataset_name)
                            print(f"⚠️  Empty: {dataset_name}")
                        else:
                            print(f"✅ Valid: {dataset_name} ({len(dataset_value)} rows)")
                    elif dataset_value is None:
                        empty_datasets.append(dataset_name)
                        print(f"⚠️  None: {dataset_name}")
                    else:
                        print(f"✅ Valid: {dataset_name}")
            
            # Summary
            print("\n" + "=" * 60)
            if missing_datasets or empty_datasets:
                print(f"❌ Dataset check FAILED")
                print(f"   Missing: {missing_datasets}")
                print(f"   Empty: {empty_datasets}")
                print(f"   Action: Will trigger fresh download")
                return False
            else:
                print(f"✅ All 8 datasets are complete and valid")
                print(f"   Action: Can proceed with incremental update")
                return True
                
        except Exception as e:
            print(f"❌ Error checking datasets: {e}")
            return False

    async def incremental_update(self, ticker: str, language: str = "English") -> Dict[str, Any]:
        """
        Main incremental update function with dataset completeness check
        
        Args:
            ticker: Stock ticker symbol
            language: Language for output
            
        Returns:
            Dictionary with update results AND all 8 datasets
        """
        print(f"🚀 Starting Incremental Update for {ticker}")
        print("=" * 80)
        
        try:
            # Initialize shared clients if needed
            if self.shared_clients is None:
                await shared_clients.initialize()
                self.shared_clients = shared_clients
            
            # Step 1: Check if ticker exists in database
            if self.db_agent.check_data_exists(ticker):
                print(f"✅ Data exists for {ticker}")
                
                # DEBUG: Check if all 8 datasets are complete
                if self.debug_check_datasets_complete(ticker):
                    print(f"🔄 All datasets complete, performing incremental update...")
                    update_result = await self._perform_incremental_update(ticker, language)
                else:
                    print(f"⚠️ Datasets incomplete, triggering fresh download...")
                    update_result = await self._generate_fresh_datasets(ticker, language)
            else:
                print(f"⚠️ No data found for {ticker}, generating fresh datasets...")
                update_result = await self._generate_fresh_datasets(ticker, language)
            
            # Step 2: After update/generation, retrieve all 8 datasets
            if update_result.get("status") == "success":
                print(f"📥 Retrieving all 8 datasets for {ticker}...")
                datasets = self.db_agent.retrieve_datasets(ticker)
                
                if datasets.get("status") == "success":
                    # Merge update metadata with actual datasets
                    final_result = {**update_result, **datasets}
                    print(f"✅ Successfully retrieved all 8 datasets for {ticker}")
                    print(f"📊 Available datasets: {[k for k in final_result.keys() if k not in ['status', 'ticker', 'update_type', 'timestamp']]}")
                    return final_result
                else:
                    print(f"❌ Failed to retrieve datasets: {datasets.get('error')}")
                    return update_result
            else:
                return update_result
            
        except Exception as e:
            print(f"❌ Incremental update failed for {ticker}: {e}")
            return {
                "status": "failed",
                "ticker": ticker,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _generate_fresh_datasets(self, ticker: str, language: str) -> Dict[str, Any]:
        """
        Generate fresh datasets for new ticker using DB Agent
        
        Args:
            ticker: Stock ticker symbol
            language: Language for output
            
        Returns:
            Dictionary with generation results
        """
        print(f"🔄 Generating fresh datasets for {ticker}...")
        
        try:
            # Call DB Agent to generate and store 8 datasets
            result = await self.db_agent.generate_and_store(ticker)
            
            if result.get("status") == "success":
                print(f"✅ Successfully generated fresh datasets for {ticker}")
                return {
                    "status": "success",
                    "ticker": ticker,
                    "update_type": "fresh_generation",
                    "datasets_generated": 8,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                raise Exception(f"DB Agent generation failed: {result.get('error')}")
            
        except Exception as e:
            print(f"❌ Fresh dataset generation failed: {e}")
            return {
                "status": "failed",
                "ticker": ticker,
                "error": str(e),
                "update_type": "fresh_generation",
                "timestamp": datetime.now().isoformat()
            }
    
    async def _perform_incremental_update(self, ticker: str, language: str) -> Dict[str, Any]:
        """
        Perform incremental update for existing ticker
        
        Args:
            ticker: Stock ticker symbol
            language: Language for output
            
        Returns:
            Dictionary with update results
        """
        print(f"🔄 Performing incremental update for {ticker}...")
        
        try:
            # Step 1: Retrieve existing data
            print("📥 Step 1: Retrieving existing data...")
            existing_data = self.db_agent.retrieve_datasets(ticker)
            
            if not existing_data or 'meta_info' not in existing_data:
                raise Exception("Failed to retrieve existing data")
            
            # Step 2: Get previous update time and check if update is needed
            previous_update_time = existing_data['meta_info']['retrieved_date']
            if 'T' in previous_update_time:
                previous_update_time = previous_update_time.split('T')[0]
            
            print(f"📅 Previous update: {previous_update_time}")
            
            # Check if data is fresh (less than 14 days old)
            try:
                previous_update_date = datetime.strptime(previous_update_time, '%Y-%m-%d')
                days_since_update = (datetime.now() - previous_update_date).days
                
                if days_since_update < 14:
                    print(f"✅ Data is fresh ({days_since_update} days old, < 14 days)")
                    print(f"⏭️  Skipping update and returning existing data from database...")
                    
                    # Return existing datasets from database
                    # Note: Only the 7-8 final computed datasets are stored, not raw input data
                    return {
                        "status": "success",
                        "ticker": ticker,
                        "update_type": "skipped_fresh_data",
                        "previous_update_time": previous_update_time,
                        "days_since_update": days_since_update,
                        "total_factors": existing_data['meta_info'].get('total_factors', 'N/A'),
                        "datasets_retrieved": len([k for k in existing_data.keys() if k.endswith('_df') or k == 'risk_share_index']),
                        "message": f"Data is fresh ({days_since_update} days old). No update needed.",
                        "timestamp": datetime.now().isoformat(),
                        # Include all stored datasets from Redis
                        "risk_share_index": existing_data.get('risk_share_index'),
                        "macro_volatility_df": existing_data.get('macro_volatility_df'),
                        "micro_volatility_df": existing_data.get('micro_volatility_df'),
                        "impact_metrics_df": existing_data.get('impact_metrics_df'),
                        "macro_total_impact_df": existing_data.get('macro_total_impact_df'),
                        "micro_total_impact_df": existing_data.get('micro_total_impact_df'),
                        "Factor_Risk_Reward": existing_data.get('Factor_Risk_Reward'),
                        "factor_time_df": existing_data.get('factor_time_df'),
                        "meta_info": existing_data.get('meta_info')
                    }
                else:
                    print(f"⚠️ Data is stale ({days_since_update} days old, >= 14 days)")
                    print(f"🔄 Proceeding with incremental update...")
                
            except Exception as e:
                print(f"⚠️ Could not parse date, proceeding with update: {e}")
            
            # Step 3: Ensure Market Expectation Agent data is fresh FIRST
            print("🔄 Step 2: Checking Market Expectation Agent data freshness...")
            try:
                # Import Market Expectation Agent to trigger update if needed
                from Sub_Agent_Folder.Market_Expectation_Agent.Stock_Trend_DB_Agent import DatabaseStorage
                
                # Create Market Expectation Agent instance (Redis type)
                market_expectation_agent = DatabaseStorage(db_type="redis")
                
                # Check if Market Expectation data needs update (24-hour threshold)
                print(f"🔍 Checking Market Expectation data for {ticker}...")
                existing_market_data = market_expectation_agent.get_stock_trend_data(ticker)
                
                if existing_market_data:
                    # Check if data is fresh (within 24 hours)
                    stored_at = existing_market_data.get('metadata', {}).get('stored_at', '')
                    if stored_at:
                        try:
                            stored_time = datetime.fromisoformat(stored_at.replace('Z', '+00:00'))
                            hours_since_update = (datetime.now() - stored_time.replace(tzinfo=None)).total_seconds() / 3600
                            
                            if hours_since_update >= 24:
                                print(f"⚠️ Market Expectation data is stale ({hours_since_update:.1f} hours old, >= 24 hours)")
                                print(f"🔄 Triggering Market Expectation Agent update for {ticker}...")
                                
                                # Trigger fresh update
                                update_result = await market_expectation_agent.update_if_stale_with_lock(ticker, force_update=True)
                                if update_result == "updated":
                                    print(f"✅ Market Expectation Agent updated successfully")
                                else:
                                    print(f"⚠️ Market Expectation Agent update result: {update_result}")
                            else:
                                print(f"✅ Market Expectation data is fresh ({hours_since_update:.1f} hours old)")
                        except Exception as e:
                            print(f"⚠️ Could not parse Market Expectation timestamp, triggering update: {e}")
                            update_result = await market_expectation_agent.update_if_stale_with_lock(ticker, force_update=True)
                    else:
                        print(f"⚠️ No stored_at timestamp in Market Expectation data, triggering update...")
                        update_result = await market_expectation_agent.update_if_stale_with_lock(ticker, force_update=True)
                else:
                    print(f"⚠️ No Market Expectation data found for {ticker}, triggering fresh download...")
                    update_result = await market_expectation_agent.update_if_stale_with_lock(ticker, force_update=True)
                
                print(f"✅ Market Expectation Agent check complete")
                
            except Exception as e:
                print(f"⚠️ Market Expectation Agent check failed: {e}")
                print(f"🔄 Proceeding with Quant Impact update anyway...")
            
            # Step 4: Generate new metrics from previous update to today
            print("🔄 Step 3: Generating new metrics...")
            new_impact_metrics_df, new_final_impact_metrics_df, new_factor_time_df = generate_update_metrics(
                ticker=ticker,
                previous_update_time=previous_update_time,
                language=language
            )
            
            # Step 5: LLM-based factor mapping and merging
            print("🤖 Step 4: LLM-based factor mapping...")
            updated_impact_metrics_df, updated_factor_time_df = await self._merge_metrics_with_llm(
                existing_data, new_impact_metrics_df, new_factor_time_df, ticker
            )
            
            # Step 6: Generate all 8 datasets using Storage Agent pipeline
            print("📊 Step 5: Generating all 8 datasets...")
            all_datasets = await self._generate_all_8_datasets(updated_impact_metrics_df, ticker, language)
            
            # Step 7: Store updated datasets (replace old ones)
            print("💾 Step 6: Storing updated datasets...")
            storage_success = self.storage_agent.store_8_datasets_as_csv(
                ticker=ticker,
                risk_share_index=all_datasets['risk_share_index'],
                macro_volatility_df=all_datasets['macro_volatility_df'],
                micro_volatility_df=all_datasets['micro_volatility_df'],
                impact_metrics_df=updated_impact_metrics_df,
                macro_total_impact_df=all_datasets['macro_total_impact_df'],
                micro_total_impact_df=all_datasets['micro_total_impact_df'],
                Factor_Risk_Reward=all_datasets['Factor_Risk_Reward'],
                factor_time_df=updated_factor_time_df,
                meta_info=all_datasets['meta_info']
            )
            
            if storage_success:
                print(f"✅ Incremental update completed successfully for {ticker}")
                return {
                    "status": "success",
                    "ticker": ticker,
                    "update_type": "incremental",
                    "previous_update_time": previous_update_time,
                    "new_factors_added": len(new_impact_metrics_df),
                    "total_factors": len(updated_impact_metrics_df),
                    "datasets_updated": 8,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                raise Exception("Failed to store updated datasets")
                
        except Exception as e:
            print(f"❌ Incremental update failed: {e}")
            return {
                "status": "failed",
                "ticker": ticker, 
                "error": str(e),
                "update_type": "incremental",
                "timestamp": datetime.now().isoformat()
            }
    
    async def _merge_metrics_with_llm(self, existing_data: Dict, new_impact_metrics_df: pd.DataFrame, 
                                     new_factor_time_df: pd.DataFrame, ticker: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        LLM-based factor mapping and merging (from update_logic.ipynb)
        
        Args:
            existing_data: Existing datasets from Redis
            new_impact_metrics_df: New impact metrics DataFrame
            new_factor_time_df: New factor time DataFrame
            ticker: Stock ticker symbol
            
        Returns:
            Tuple of (updated_impact_metrics_df, updated_factor_time_df)
        """
        print("🤖 Performing LLM-based factor mapping...")
        
        try:
            # Extract existing impact metrics
            old_impact_metrics_df = existing_data['impact_metrics_df']
            old_factor_time_df = existing_data['factor_time_df']
            
            # Step 1: Merge impact metrics using LLM
            merged_impact_df = self._merge_impact_metrics_with_llm(
                new_impact_metrics_df, old_impact_metrics_df, ticker
            )
            
            # Step 2: Update impact metrics with new factor data
            updated_impact_metrics_df = self._update_impact_metrics_with_new_factors(
                merged_impact_df, new_impact_metrics_df
            )
            
            # Step 3: Merge factor time data using LLM
            updated_factor_time_df = self._merge_factor_time_data_with_llm(
                old_factor_time_df, new_factor_time_df, ticker
            )
            
            print(f"✅ LLM-based merging completed")
            print(f"   📊 Updated impact metrics: {len(updated_impact_metrics_df)} factors")
            print(f"   📅 Updated factor time: {len(updated_factor_time_df)} intervals")
            
            return updated_impact_metrics_df, updated_factor_time_df
            
        except Exception as e:
            print(f"❌ LLM merging failed: {e}")
            # Fallback to simple concatenation
            return self._fallback_merge(existing_data, new_impact_metrics_df, new_factor_time_df)
    
    def _merge_impact_metrics_with_llm(self, new_impact_df: pd.DataFrame, old_impact_metrics_df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """
        Merge new and old impact metrics using LLM-based factor mapping
        (Copied from update_logic.ipynb)
        """
        print(f"🔄 Merging impact metrics for {ticker}...")
        
        # Extract factor names
        new_factors = self._extract_factor_names(new_impact_df)
        old_factors = self._extract_factor_names(old_impact_metrics_df)
        
        print(f"📊 New factors: {len(new_factors)}")
        print(f"📊 Old factors: {len(old_factors)}")
        
        # Get LLM mapping
        print("🤖 Getting LLM factor mapping...")
        mapping_result = self._map_factors_with_llm(new_factors, old_factors, ticker)
        
        # Start with old impact metrics as base - keep only essential columns
        essential_columns = [
            'scope', 'factor', 'trend_count', 'weighted_mean', 'weighted_variance',
            'average_duration', 'total_duration', 'trend_weight_score',
            'score_weighted_mean', 'score_weighted_variance', 'risk_reward_ratio'
        ]
        
        # Filter to only keep essential columns that exist
        available_columns = [col for col in essential_columns if col in old_impact_metrics_df.columns]
        merged_df = old_impact_metrics_df[available_columns].copy()
        
        # Add mapping column
        merged_df['mapping_new_factors'] = ""
        
        # Process each new factor
        for mapping in mapping_result.get('mappings', []):
            new_factor = mapping['new_factor']
            mapping_type = mapping['type']
            
            if mapping_type == 'existing':
                # Map to existing factor
                existing_index = mapping['existing_index']
                existing_factor = mapping['existing_factor']
                
                print(f"✅ Mapping '{new_factor}' → '{existing_factor}' (index {existing_index})")
                
                # Add to mapping column
                if merged_df.iloc[existing_index]['mapping_new_factors']:
                    merged_df.iloc[existing_index, merged_df.columns.get_loc('mapping_new_factors')] += f", {new_factor}"
                else:
                    merged_df.iloc[existing_index, merged_df.columns.get_loc('mapping_new_factors')] = new_factor
                    
            elif mapping_type == 'new':
                # Add as new row
                print(f"➕ Adding new factor: '{new_factor}'")
                
                # Get the new factor's data
                if 'factor' in new_impact_df.columns:
                    new_factor_data = new_impact_df[new_impact_df['factor'] == new_factor].iloc[0]
                elif 'factor_name' in new_impact_df.columns:
                    new_factor_data = new_impact_df[new_impact_df['factor_name'] == new_factor].iloc[0]
                else:
                    print(f"❌ Cannot find factor column in new_impact_df")
                    continue
                
                # Create new row with only essential columns
                new_row = {}
                for col in available_columns:
                    if col in new_factor_data:
                        new_row[col] = new_factor_data[col]
                    else:
                        new_row[col] = None
                
                new_row['mapping_new_factors'] = ""
                
                # Add to merged DataFrame
                merged_df = pd.concat([merged_df, pd.DataFrame([new_row])], ignore_index=True)
        
        print(f"✅ Merge completed: {len(merged_df)} total factors")
        return merged_df
    
    def _extract_factor_names(self, impact_df: pd.DataFrame) -> List[str]:
        """Extract factor names from impact metrics DataFrame"""
        if 'factor' in impact_df.columns:
            return impact_df['factor'].tolist()
        elif 'factor_name' in impact_df.columns:
            return impact_df['factor_name'].tolist()
        elif impact_df.index.name == 'factor_name':
            return impact_df.index.tolist()
        else:
            return [str(idx) for idx in impact_df.index]
    
    def _map_factors_with_llm(self, new_factors: List[str], old_factors: List[str], ticker: str) -> Dict[str, Any]:
        """Use LLM to map new factors to old factors or identify new ones"""
        llm_agent = LLMCallAgent()
        
        prompt = f"""
You are a financial factor mapping expert. I need you to map new factors to existing factors for {ticker} stock analysis.

EXISTING FACTORS:
{json.dumps(old_factors, indent=2)}

NEW FACTORS:
{json.dumps(new_factors, indent=2)}

TASK:
1. For each new factor, determine if it's similar to any existing factor
2. If similar, provide the index of the existing factor (0-based)
3. If not similar, mark it as "new"

OUTPUT FORMAT (JSON):
{{
    "mappings": [
        {{
            "new_factor": "factor_name",
            "type": "existing" or "new",
            "existing_index": 0,  // only if type is "existing"
            "existing_factor": "existing_factor_name"  // only if type is "existing"
        }}
    ]
}}

RULES:
- Be conservative: only map if factors are clearly similar (same concept, different wording)
- Consider synonyms, abbreviations, and different phrasings
- If unsure, mark as "new"
- Focus on financial and market impact concepts
"""
        
        try:
            response = llm_agent.call_deepseek(prompt)
            
            # Parse JSON response
            if isinstance(response, str):
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                if start_idx != -1 and end_idx != 0:
                    json_str = response[start_idx:end_idx]
                    result = json.loads(json_str)
                else:
                    raise ValueError("No valid JSON found in response")
            else:
                result = response
                
            return result
            
        except Exception as e:
            print(f"❌ LLM mapping failed: {e}")
            # Fallback: mark all as new
            return {
                "mappings": [
                    {
                        "new_factor": factor,
                        "type": "new"
                    }
                    for factor in new_factors
                ]
            }
    
    def _update_impact_metrics_with_new_factors(self, merged_df: pd.DataFrame, new_impact_df: pd.DataFrame) -> pd.DataFrame:
        """
        Update impact metrics with new factor data (from update_logic.ipynb)
        """
        print("🔄 Updating impact metrics with new factor data...")
        
        # Create a copy of merged_df to work with
        updated_df = merged_df.copy()
        
        # Get new factor names
        new_factors = self._extract_factor_names(new_impact_df)
        
        # For each new factor, update the corresponding row in merged_df
        for new_factor in new_factors:
            # Find the row in merged_df that corresponds to this new factor
            if 'factor' in updated_df.columns:
                factor_mask = updated_df['factor'] == new_factor
            elif 'factor_name' in updated_df.columns:
                factor_mask = updated_df['factor_name'] == new_factor
            else:
                continue
            
            if factor_mask.any():
                # Get the new factor's data
                if 'factor' in new_impact_df.columns:
                    new_factor_data = new_impact_df[new_impact_df['factor'] == new_factor].iloc[0]
                elif 'factor_name' in new_impact_df.columns:
                    new_factor_data = new_impact_df[new_impact_df['factor_name'] == new_factor].iloc[0]
                else:
                    continue
                
                # Update the row with new data
                for col in updated_df.columns:
                    if col in new_factor_data and col != 'mapping_new_factors':
                        updated_df.loc[factor_mask, col] = new_factor_data[col]
        
        print(f"✅ Updated impact metrics: {len(updated_df)} factors")
        return updated_df
    
    def _merge_factor_time_data_with_llm(self, old_factor_time_df: pd.DataFrame, new_factor_time_df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """
        Merge factor time data using LLM (from update_logic.ipynb)
        """
        print("🔄 Merging factor time data...")
        
        try:
            # Get factor names from both DataFrames
            old_factors = self._extract_factor_names(old_factor_time_df)
            new_factors = self._extract_factor_names(new_factor_time_df)
            
            print(f"📊 Old factor time factors: {len(old_factors)}")
            print(f"📊 New factor time factors: {len(new_factors)}")
            
            # Get LLM mapping for factor time data
            mapping_result = self._map_factors_with_llm(new_factors, old_factors, ticker)
            
            # Start with old factor time data as base
            merged_factor_time_df = old_factor_time_df.copy()
            
            # Process each new factor
            for mapping in mapping_result.get('mappings', []):
                new_factor = mapping['new_factor']
                mapping_type = mapping['type']
                
                if mapping_type == 'existing':
                    # Map to existing factor - update the existing row
                    existing_index = mapping['existing_index']
                    existing_factor = mapping['existing_factor']
                    
                    print(f"✅ Updating factor time for '{new_factor}' → '{existing_factor}' (index {existing_index})")
                    
                    # Get the new factor's time data
                    if 'factor_name' in new_factor_time_df.columns:
                        new_factor_data = new_factor_time_df[new_factor_time_df['factor_name'] == new_factor].iloc[0]
                    elif 'factor' in new_factor_time_df.columns:
                        new_factor_data = new_factor_time_df[new_factor_time_df['factor'] == new_factor].iloc[0]
                    else:
                        continue
                    
                    # Update the existing row with new time data
                    for col in merged_factor_time_df.columns:
                        if col in new_factor_data:
                            merged_factor_time_df.iloc[existing_index, merged_factor_time_df.columns.get_loc(col)] = new_factor_data[col]
                            
                elif mapping_type == 'new':
                    # Add as new row
                    print(f"➕ Adding new factor time: '{new_factor}'")
                    
                    # Get the new factor's time data
                    if 'factor_name' in new_factor_time_df.columns:
                        new_factor_data = new_factor_time_df[new_factor_time_df['factor_name'] == new_factor].iloc[0]
                    elif 'factor' in new_factor_time_df.columns:
                        new_factor_data = new_factor_time_df[new_factor_time_df['factor'] == new_factor].iloc[0]
                    else:
                        continue
                    
                    # Create new row
                    new_row = {}
                    for col in merged_factor_time_df.columns:
                        if col in new_factor_data:
                            new_row[col] = new_factor_data[col]
                        else:
                            new_row[col] = None
                    
                    # Add to merged DataFrame
                    merged_factor_time_df = pd.concat([merged_factor_time_df, pd.DataFrame([new_row])], ignore_index=True)
            
            print(f"✅ Factor time merge completed: {len(merged_factor_time_df)} intervals")
            return merged_factor_time_df
            
        except Exception as e:
            print(f"❌ Factor time merge failed: {e}")
            # Fallback: simple concatenation
            return pd.concat([old_factor_time_df, new_factor_time_df], ignore_index=True)
    
    async def _generate_all_8_datasets(self, updated_impact_metrics_df: pd.DataFrame, ticker: str, language: str) -> Dict[str, Any]:
        """
        Generate all 8 datasets using Storage Agent pipeline
        """
        print("📊 Generating all 8 datasets using Storage Agent pipeline...")
        
        try:
            # Step 1: Generate risk analysis datasets (6 datasets)
            risk_share_index, macro_volatility_df, micro_volatility_df, impact_metrics_df, macro_total_impact_df, micro_total_impact_df = quant_impact_risk_analysis(updated_impact_metrics_df)
            
            # Step 2: Generate impact summary schema
            schema_result = generate_impact_summary_schema(updated_impact_metrics_df, language)
            
            # Step 3: Convert schema to compound datasets
            Factor_Risk_Reward = convert_schema_to_compound_datasets(schema_result, updated_impact_metrics_df)
            
            # Step 4: Create meta info
            meta_info = {
                "ticker": ticker,
                "status": "success",
                "update_type": "incremental",
                "retrieved_date": datetime.now().isoformat(),
                "total_factors": len(updated_impact_metrics_df),
                "language": language
            }
            
            print("✅ All 8 datasets generated successfully")
            
            return {
                "risk_share_index": risk_share_index,
                "macro_volatility_df": macro_volatility_df,
                "micro_volatility_df": micro_volatility_df,
                "impact_metrics_df": impact_metrics_df,
                "macro_total_impact_df": macro_total_impact_df,
                "micro_total_impact_df": micro_total_impact_df,
                "Factor_Risk_Reward": Factor_Risk_Reward,
                "meta_info": meta_info
            }
            
        except Exception as e:
            print(f"❌ Dataset generation failed: {e}")
            raise e
    
    def _fallback_merge(self, existing_data: Dict, new_impact_metrics_df: pd.DataFrame, new_factor_time_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Fallback merge when LLM fails - simple concatenation
        """
        print("⚠️ Using fallback merge (simple concatenation)")
        
        # Simple concatenation for impact metrics
        old_impact_metrics_df = existing_data['impact_metrics_df']
        updated_impact_metrics_df = pd.concat([old_impact_metrics_df, new_impact_metrics_df], ignore_index=True)
        
        # Simple concatenation for factor time
        old_factor_time_df = existing_data['factor_time_df']
        updated_factor_time_df = pd.concat([old_factor_time_df, new_factor_time_df], ignore_index=True)
        
        return updated_impact_metrics_df, updated_factor_time_df

# =============================================================================
# USAGE FUNCTIONS
# =============================================================================

async def run_incremental_update(ticker: str, language: str = "English") -> Dict[str, Any]:
    """
    Convenience function to run incremental update
    
    Args:
        ticker: Stock ticker symbol
        language: Language for output
        
    Returns:
        Update results summary
    """
    agent = QuantImpactIncrementalUpdate()
    return await agent.incremental_update(ticker, language)

# =============================================================================
# TESTING FUNCTION
# =============================================================================

async def test_incremental_update():
    """Test function for the incremental update system"""
    print("🧪 Testing Incremental Update System")
    print("=" * 80)
    
    try:
        # Test with PYPL
        result = await run_incremental_update("PYPL")
        
        print("\n📊 Test Results:")
        print(f"Status: {result['status']}")
        print(f"Update Type: {result.get('update_type', 'unknown')}")
        if result.get('update_type') == 'incremental':
            print(f"Previous Update: {result.get('previous_update_time', 'unknown')}")
            print(f"New Factors Added: {result.get('new_factors_added', 0)}")
            print(f"Total Factors: {result.get('total_factors', 0)}")
        print(f"Datasets: {result.get('datasets_updated', result.get('datasets_generated', 0))}")
        
        return result
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return {"status": "failed", "error": str(e)}

if __name__ == "__main__":
    # Run test if executed directly
    result = asyncio.run(test_incremental_update())
    print(f"\nFinal Result: {result}")
