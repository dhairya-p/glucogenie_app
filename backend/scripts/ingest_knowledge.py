"""Script to ingest knowledge into RAG indexes."""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.rag_service import get_rag_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ingest_drug_database():
    """Ingest drug interaction database."""
    rag = get_rag_service()
    
    # Example: Load from Drugs.com or FDA database
    # In production, load from actual drug interaction database
    drugs = [
        "Metformin: Used for Type 2 diabetes. Contraindicated in kidney disease (GFR < 30). Side effects: GI upset, lactic acidosis (rare).",
        "Insulin: Used for Type 1 and Type 2 diabetes. Can cause hypoglycemia. Must be taken with meals.",
        "Metformin + Insulin: Safe combination. Monitor for hypoglycemia. No major interactions.",
        "Sulfonylureas (e.g., Glipizide): Can cause hypoglycemia. Avoid alcohol. Monitor blood glucose closely.",
        "DPP-4 inhibitors (e.g., Sitagliptin): Generally safe, low risk of hypoglycemia. Can be combined with metformin.",
        "GLP-1 agonists (e.g., Liraglutide): Injectable medication. Can cause nausea. Helps with weight loss.",
        "SGLT2 inhibitors (e.g., Canagliflozin): Can cause urinary tract infections. Monitor for dehydration.",
        "Thiazolidinediones (e.g., Pioglitazone): Can cause fluid retention. Monitor for heart failure symptoms.",
        "Alpha-glucosidase inhibitors (e.g., Acarbose): Taken with meals. Can cause GI side effects.",
        "Meglitinides (e.g., Repaglinide): Short-acting. Taken before meals. Can cause hypoglycemia.",
    ]
    
    try:
        rag.ingest_documents(drugs, index_type="drug")
        logger.info(f"Ingested {len(drugs)} drug documents")
    except Exception as exc:
        logger.error(f"Error ingesting drug database: {exc}", exc_info=True)


def ingest_food_database():
    """Ingest Singapore food database."""
    rag = get_rag_service()
    
    # Try to load from singapore_foods.json if it exists
    food_file = backend_dir / "data" / "singapore_foods.json"
    
    if food_file.exists():
        try:
            with open(food_file) as f:
                foods = json.load(f)
            
            food_docs = []
            for food in foods:
                doc = f"""
                {food.get('name', 'Unknown')} ({food.get('cuisine', 'Unknown')} cuisine)
                - Serving: {food.get('serving_size', 'Unknown')}
                - Carbs: {food.get('carbs_g', 'Unknown')}g
                - GI: {food.get('glycemic_index', 'Unknown')}
                - GL: {food.get('glycemic_load', 'Unknown')}
                - Halal: {'Yes' if food.get('is_halal', False) else 'No'}
                - Vegetarian: {'Yes' if food.get('is_vegetarian', False) else 'No'}
                - Description: {food.get('description', '')}
                - Tips: {food.get('preparation_notes', '')}
                """
                food_docs.append(doc)
            
            rag.ingest_documents(food_docs, index_type="food")
            logger.info(f"Ingested {len(food_docs)} food documents")
        except Exception as exc:
            logger.error(f"Error loading food database from file: {exc}", exc_info=True)
    else:
        # Use example foods if file doesn't exist
        example_foods = [
            "Chicken Rice: Popular Singapore dish. 1 plate contains ~60g carbs. GI: 65 (medium). Tip: Request brown rice, reduce rice portion to 3/4.",
            "Laksa: Spicy noodle soup. 1 bowl contains ~55g carbs. GI: 60 (medium). Tip: Reduce noodles, add more vegetables.",
            "Roti Prata: Indian flatbread. 2 pieces contain ~45g carbs. GI: 70 (high). Tip: Eat with curry instead of sugar, limit to 1 piece.",
            "Char Kway Teow: Stir-fried noodles. 1 plate contains ~70g carbs. GI: 75 (high). Tip: Share portion, add vegetables.",
            "Hainanese Chicken Rice: Classic dish. 1 plate contains ~60g carbs. GI: 65 (medium). Tip: Choose brown rice, remove skin from chicken.",
            "Bak Kut Teh: Pork rib soup. 1 bowl contains ~10g carbs. GI: Low. Good choice for diabetes patients.",
            "Yong Tau Foo: Tofu and vegetables in soup. 1 bowl contains ~25g carbs. GI: 40 (low). Excellent choice for diabetes patients.",
            "Fish Soup: Light soup with fish. 1 bowl contains ~15g carbs. GI: Low. Good choice for diabetes patients.",
        ]
        
        try:
            rag.ingest_documents(example_foods, index_type="food")
            logger.info(f"Ingested {len(example_foods)} example food documents")
        except Exception as exc:
            logger.error(f"Error ingesting example foods: {exc}", exc_info=True)


def ingest_clinical_guidelines():
    """Ingest clinical guidelines."""
    rag = get_rag_service()
    
    # Example: ADA Standards of Care, MOH guidelines
    guidelines = [
        "HbA1c target for most adults with diabetes: <7% (ADA 2025)",
        "HbA1c target for elderly (>65 years) or frail patients: <8% to reduce hypoglycemia risk",
        "Fasting glucose target: 80-130 mg/dL (ADA 2025)",
        "Postprandial glucose target: <180 mg/dL (ADA 2025)",
        "Pre-meal glucose target: 80-130 mg/dL (ADA 2025)",
        "Bedtime glucose target: 90-150 mg/dL (ADA 2025)",
        "Hypoglycemia: Blood glucose <70 mg/dL requires treatment",
        "Severe hypoglycemia: Blood glucose <54 mg/dL is dangerous and requires immediate treatment",
        "Hyperglycemia: Blood glucose >250 mg/dL may require medical attention",
        "Diabetic ketoacidosis (DKA): Blood glucose >250 mg/dL with ketones requires emergency care",
        "Exercise: 150 minutes of moderate-intensity exercise per week recommended",
        "Diet: Focus on whole grains, vegetables, lean proteins. Limit refined carbs and sugars.",
        "Medication adherence: Take medications as prescribed. Don't skip doses.",
        "Blood glucose monitoring: Check 4-7 times per day for insulin users, 1-2 times for others.",
        "Foot care: Inspect feet daily. Report any wounds or changes immediately.",
    ]
    
    try:
        rag.ingest_documents(guidelines, index_type="clinical")
        logger.info(f"Ingested {len(guidelines)} clinical guidelines")
    except Exception as exc:
        logger.error(f"Error ingesting clinical guidelines: {exc}", exc_info=True)


if __name__ == "__main__":
    logger.info("Starting knowledge ingestion...")
    
    # Check for Pinecone API key
    if not os.getenv("PINECONE_API_KEY"):
        logger.warning("PINECONE_API_KEY not found. RAG service will use fallback responses.")
        logger.info("To enable RAG, set PINECONE_API_KEY environment variable.")
    
    ingest_drug_database()
    ingest_food_database()
    ingest_clinical_guidelines()
    
    logger.info("Knowledge ingestion complete!")
