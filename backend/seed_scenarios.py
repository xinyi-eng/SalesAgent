"""
Database seeder for practice scenarios
Run this script to seed the database with more practice scenarios extracted from knowledge base
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal, Base
from app.models.practice import Scenario
import uuid
from datetime import datetime

# Scenarios extracted from SPIN Selling knowledge base
SEED_SCENARIOS = [
    {
        "name": "首次拜访客户",
        "description": "练习如何进行客户的首次拜访，包括开场白、建立信任、了解客户背景。SPIN销售巨人强调开场破冰阶段不要过早提及产品方案。",
        "type": "首次拜访",
        "category": "通用",
        "sub_category": "基础训练",
        "is_builtin": True,
        "default_role_config": {
            "customer_type": "assertive",
            "difficulty": "easy",
            "opening_focus": "建立信任而非推销"
        }
    },
    {
        "name": "挖掘客户需求(SPIN)",
        "description": "练习使用SPIN四类问题挖掘客户需求：现状问题(Situation)、难点问题(Problem)、暗示问题(Implication)、需求-效益问题(Need-Payoff)。这是大生意销售的核心技能。",
        "type": "需求挖掘",
        "category": "通用",
        "sub_category": "SPIN训练",
        "is_builtin": True,
        "default_role_config": {
            "customer_type": "analytical",
            "difficulty": "medium",
            "spin_focus": "四类问题综合运用"
        }
    },
    {
        "name": "处理价格异议",
        "description": "练习处理客户对价格的异议。研究表明，单纯的折扣策略效果有限，应该通过暗示问题积聚需求价值，让客户认识到解决方案的真正价值。",
        "type": "异议处理",
        "category": "通用",
        "sub_category": "异议处理",
        "is_builtin": True,
        "default_role_config": {
            "customer_type": "price_oriented",
            "difficulty": "hard",
            "objection_type": "价格异议"
        }
    },
    {
        "name": "处理能力异议",
        "description": "练习处理客户对供应商能力或产品性能的质疑。分为'没有能力的异议'和'有能力但客户不认可的异议'，需要不同的应对策略。",
        "type": "异议处理",
        "category": "通用",
        "sub_category": "异议处理",
        "is_builtin": True,
        "default_role_config": {
            "customer_type": "risk_averse",
            "difficulty": "hard",
            "objection_type": "能力异议"
        }
    },
    {
        "name": "产品方案呈现",
        "description": "练习如何清晰呈现产品方案和价值主张。区分'A类利益(优点)'和'B类利益'，B类利益直接满足客户明确需求，更有效。",
        "type": "产品讲解",
        "category": "通用",
        "sub_category": "产品培训",
        "is_builtin": True,
        "default_role_config": {
            "customer_type": "analytical",
            "difficulty": "medium",
            "presentation_focus": "利益陈述而非特征罗列"
        }
    },
    {
        "name": "电话销售跟进",
        "description": "练习电话销售场景，包括：快速建立信任、引起兴趣、处理电话中的异议、约定进一步会面。电话销售需要更简洁的话术。",
        "type": "电话销售",
        "category": "通用",
        "sub_category": "渠道销售",
        "is_builtin": True,
        "default_role_config": {
            "customer_type": "expressive",
            "difficulty": "medium",
            "channel": "电话"
        }
    },
    {
        "name": "大客户开发",
        "description": "练习大型复杂销售中的客户开发。涉及决策链、多个利益相关者、长周期。需要使用进展承诺而非立即成交。",
        "type": "大客户销售",
        "category": "通用",
        "sub_category": "大生意",
        "is_builtin": True,
        "default_role_config": {
            "customer_type": "decision_maker",
            "difficulty": "hard",
            "deal_size": "large"
        }
    },
    {
        "name": "促成成交技巧",
        "description": "练习在大生意中获取正确类型的承诺。研究发现，收场白技巧在小生意有效但在大生意中反而有害。需要使用需求-效益问题来自然促成。",
        "type": "促成成交",
        "category": "通用",
        "sub_category": "成交技巧",
        "is_builtin": True,
        "default_role_config": {
            "customer_type": "decisive",
            "difficulty": "hard",
            "closing_focus": "进展承诺 vs 购买承诺"
        }
    },
    {
        "name": "防御性销售(异议防范)",
        "description": "练习在提出解决方案之前先开发客户需求，通过暗示问题和需求-效益问题积聚价值，从根本上防止异议产生。",
        "type": "防御销售",
        "category": "通用",
        "sub_category": "高级技巧",
        "is_builtin": True,
        "default_role_config": {
            "customer_type": "amiable",
            "difficulty": "hard",
            "strategy": "先开发需求再提方案"
        }
    },
    {
        "name": "客户拒绝挽回",
        "description": "练习当客户表示拒绝或说'不需要'时的挽回话术。不是直接反驳，而是重新定义需求，发现客户的隐含需求。",
        "type": "异议处理",
        "category": "通用",
        "sub_category": "异议处理",
        "is_builtin": True,
        "default_role_config": {
            "customer_type": "rejection",
            "difficulty": "medium",
            "objection_type": "拒绝/不需要"
        }
    },
    {
        "name": "再次拜访与跟进",
        "description": "练习对已有客户的再次拜访和跟进策略。保持关系、发现新需求、推进销售进展。",
        "type": "再次拜访",
        "category": "通用",
        "sub_category": "客户维护",
        "is_builtin": True,
        "default_role_config": {
            "customer_type": "relationship_oriented",
            "difficulty": "easy",
            "visit_type": "跟进"
        }
    },
    {
        "name": "竞品对比应对",
        "description": "练习当客户提到竞争对手时如何应对。不贬低竞品，而是突出自身差异化价值。",
        "type": "竞品对比",
        "category": "通用",
        "sub_category": "竞争销售",
        "is_builtin": True,
        "default_role_config": {
            "customer_type": "comparative",
            "difficulty": "medium",
            "scenario": "客户提及竞争对手"
        }
    }
]


def seed_scenarios():
    """Seed the database with practice scenarios"""
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check existing scenarios
        existing = db.query(Scenario).filter(Scenario.is_builtin == True).all()
        existing_names = [s.name for s in existing]

        print(f"Found {len(existing)} existing builtin scenarios")
        print(f"Existing: {existing_names}")

        added_count = 0
        updated_count = 0

        for scenario_data in SEED_SCENARIOS:
            name = scenario_data["name"]

            # Check if scenario already exists
            existing_scenario = db.query(Scenario).filter(Scenario.name == name).first()

            if existing_scenario:
                # Update existing scenario
                for key, value in scenario_data.items():
                    if key != "id":
                        setattr(existing_scenario, key, value)
                existing_scenario.updated_at = datetime.utcnow()
                updated_count += 1
                print(f"Updated: {name}")
            else:
                # Create new scenario
                new_scenario = Scenario(
                    id=str(uuid.uuid4()),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    **scenario_data
                )
                db.add(new_scenario)
                added_count += 1
                print(f"Added: {name}")

        db.commit()
        print(f"\nSeeding complete!")
        print(f"Added: {added_count} scenarios")
        print(f"Updated: {updated_count} scenarios")

    except Exception as e:
        print(f"Error seeding scenarios: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_scenarios()