import datetime
import os
from pathlib import Path

import yaml
import re
import logging
from typing import List, Dict, Any

logging.basicConfig(
    filename="llm.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

class PolicyViolation(Exception):
    def __init__(self, rule_id: str, message: str):
        self.rule_id = rule_id
        self.message = message
        super().__init__(f"Blocked by rule '{rule_id}': {message}")


class PolicyRule:
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id")
        self.enabled = data.get("enabled", True)
        self.stage = data.get("stage", "pre")
        self.kind = data.get("kind", "regex")
        self.pattern = data.get("pattern")
        self.flags = data.get("flags", "")
        self.action = data.get("action")
        self.priority = data.get("priority", 100)
        self.message = data.get("message", "")
        self.redact_with = data.get("redact_with", "[REDACTED]")

        re_flags = 0
        if "i" in self.flags:
            re_flags |= re.IGNORECASE
        self.regex = re.compile(self.pattern, re_flags)

    def apply(self, text: str, truncate: bool = False) -> str:
        if not self.enabled:
            return text

        matches = list(self.regex.finditer(text))
        if not matches:
            return text

        if self.action == "block":
            def replacer(match):
                orig = match.group()
                logging.info(
                    f"BLOCK rule '{self.id}': found '{orig}' replaced with '[BLOCKED]', message: {self.message}"
                )
                if truncate:
                    raise PolicyViolation(self.id, orig)
                return "[BLOCKED]"

            return self.regex.sub(replacer, text)

        elif self.action == "redact":
            def replacer(match):
                orig = match.group()
                logging.info(
                    f"REDACT rule '{self.id}': found '{orig}' replaced with '{self.redact_with}', message: {self.message}"
                )
                return self.redact_with

            return self.regex.sub(replacer, text)

        elif self.action == "flag":
            for m in matches:
                logging.info(f"FLAG rule '{self.id}': found '{m.group()}', message: {self.message}")
            return text

        return text


class PolicyEngine:
    def __init__(self, policies_dir: Path = Path(__file__).resolve().parent.parent.parent / 'policies'):
        self.revision = 1
        self.policies_dir = policies_dir
        self.rules: List[PolicyRule] = []
        self.load_policies()
        self.loaded_at = datetime.datetime.now()

    def load_policies(self):
        """Загрузить все правила из yaml файлов"""
        rules: List[PolicyRule] = []
        for file in os.listdir(self.policies_dir):
            if file.endswith(".yaml") or file.endswith(".yml"):
                with open(os.path.join(self.policies_dir, file), "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, list):
                        for rule in data:
                            rules.append(PolicyRule(rule))
        self.rules = sorted(rules, key=lambda r: r.priority)


    def refresh(self):
        self.load_policies()
        self.loaded_at = datetime.datetime.now()
        self.revision += 1


    def apply(self, text: str, stage: str = "post", truncate: bool = False) -> str:
        result = text
        for rule in self.rules:
            if rule.stage != stage:
                continue
            result = rule.apply(result,truncate=truncate)
        return result

    def list_rules(self):
        rules_list = []
        for rule in self.rules:
            rules_list.append({
                "id": rule.id,
                "enabled": rule.enabled,
                "stage": rule.stage,
                "action": rule.action,
                "priority": rule.priority,
                "message": rule.message,
                "pattern": rule.pattern,
                "redact_with": getattr(rule, "redact_with", None)
            })
        return rules_list


engine = PolicyEngine()
