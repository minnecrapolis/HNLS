#!/usr/bin/env python3
"""Validate release defaults using the captured real JSON Schema and parse templates."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src/controller/server'))
def check():
    from jsonschema import Draft202012Validator
    from jinja2 import Environment
    from libs.webserver.schemas.config_validator_service import schema
    config=json.loads((ROOT/'src/controller/server/libs/config_template.json').read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(config)
    assert not config['device_configs']
    assert config['default_device']['effects']['last_effect']=='effect_off'
    env=Environment();templates=list((ROOT/'src/controller/server/libs/app/templates').rglob('*.html'))
    for p in templates:env.parse(p.read_text())
    print('PASS: default JSON schema and',len(templates),'Jinja templates.')
if __name__=='__main__':check()
