from flask import Blueprint, jsonify, request
from flask_login import login_required
from flask_openapi import swag_from
from libs.webserver.executer import Executer
from libs.webserver.executer_base import validate_schema
from libs.webserver.messages import (
    DeviceLimitReached,
    DeviceNotFound,
    GroupAlreadyExists,
    GroupLimitReached,
    GroupNotFound,
    UnprocessableEntity,
)
from libs.webserver.schemas.device_api_schema import CREATE_GROUP_SCHEMA, DELETE_DEVICE_SCHEMA, DELETE_GROUP_SCHEMA

device_api = Blueprint("device_api", __name__)


@device_api.get("/api/system/devices")
@login_required
@swag_from("docs/device_api/get_devices.yml")
def get_devices():
    data_out = Executer.instance.device_executer.get_devices()

    return jsonify(data_out)


@device_api.post("/api/system/devices")
@login_required
@swag_from("docs/device_api/create_device.yml")
def create_device():
    data_out = Executer.instance.device_executer.create_new_device()

    if data_out is DeviceLimitReached:
        return DeviceLimitReached.as_response()

    return jsonify(data_out)


@device_api.delete("/api/system/devices")
@login_required
@swag_from("docs/device_api/delete_device.yml")
def delete_device():
    data_in = request.get_json()

    if not validate_schema(data_in, DELETE_DEVICE_SCHEMA):
        return UnprocessableEntity.as_response()

    data_out = Executer.instance.device_executer.delete_device(data_in["device"])

    if data_out is DeviceNotFound:
        return DeviceNotFound.as_response()

    return jsonify(data_out)


@device_api.get("/api/system/groups")
@login_required
@swag_from("docs/device_api/get_groups.yml")
def get_groups():
    data_out = Executer.instance.device_executer.get_groups()

    return jsonify(data_out)


@device_api.post("/api/system/groups")
@login_required
@swag_from("docs/device_api/create_group.yml")
def create_group():
    data_in = request.get_json()

    if not validate_schema(data_in, CREATE_GROUP_SCHEMA):
        return UnprocessableEntity.as_response()

    data_out = Executer.instance.device_executer.create_new_group(data_in["group"])

    if data_out is GroupLimitReached:
        return GroupLimitReached.as_response()

    if data_out is GroupAlreadyExists:
        return GroupAlreadyExists.as_response()

    return jsonify(data_out)


@device_api.delete("/api/system/groups")
@login_required
@swag_from("docs/device_api/delete_group.yml")
def delete_group():
    data_in = request.get_json()

    if not validate_schema(data_in, DELETE_GROUP_SCHEMA):
        return UnprocessableEntity.as_response()

    data_out = Executer.instance.device_executer.delete_group(data_in["group"])

    if data_out is GroupNotFound:
        return GroupNotFound.as_response()

    return jsonify(data_out)


@device_api.patch("/api/system/groups")
@login_required
@swag_from("docs/device_api/remove_invalid_device_groups.yml")
def remove_invalid_device_groups():
    data_out = Executer.instance.device_executer.remove_invalid_device_groups()

    return jsonify(data_out)


@device_api.get('/api/system/gpio-strings')
@login_required
def gpio_strings_state():
    from libs.gpio_outputs import native_devices, spi_state
    executer=Executer.instance.device_executer
    return jsonify(spi=spi_state(),devices=[{'id':key,'name':d['device_name'],'count':d['led_count'],'gpio':d['output']['output_raspi']['led_pin']} for key,d in native_devices(executer._config)])


@device_api.post('/api/system/gpio-strings')
@login_required
def gpio_string_add():
    from libs.gpio_outputs import add_string
    try:
        return jsonify(add_string(Executer.instance.device_executer,request.get_json(silent=True)))
    except (ValueError,TypeError,KeyError,OSError) as exc:
        return jsonify(error=str(exc)),400


@device_api.post('/api/system/gpio-strings/prepare')
@login_required
def gpio_string_prepare():
    from libs.gpio_outputs import prepare_spi
    try:
        return jsonify(prepare_spi())
    except (ValueError,OSError) as exc:
        return jsonify(error=str(exc)),400


@device_api.post('/api/system/gpio-strings/reboot')
@login_required
def gpio_string_reboot():
    import subprocess
    subprocess.Popen(['/usr/bin/systemctl','reboot'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return jsonify(ok=True,message='Pi reboot requested')


@device_api.get('/api/system/remote-pis')
@login_required
def remote_pis_list():
    from libs.remote_pixels import list_remote
    return jsonify(list_remote(Executer.instance.device_executer))


@device_api.post('/api/system/remote-pis')
@login_required
def remote_pi_add():
    from libs.remote_pixels import add_remote
    try:
        return jsonify(add_remote(Executer.instance.device_executer,request.get_json(silent=True)))
    except (ValueError,TypeError,KeyError,OSError) as exc:
        return jsonify(error=str(exc)),400


@device_api.post('/api/system/remote-pis/status')
@login_required
def remote_pi_status():
    from libs.remote_pixels import load, call
    data=request.get_json(silent=True) or {}
    if not isinstance(data,dict) or not isinstance(data.get('device'),str):
        return jsonify(error='Choose a remote device'),400
    nodes=load()
    key=data.get('device')
    if key not in nodes or key not in Executer.instance.device_executer._config['device_configs']:
        return jsonify(error='Remote device not found'),404
    try:
        return jsonify(call(nodes[key]))
    except ValueError as exc:
        return jsonify(error=str(exc)),400


@device_api.get('/api/system/color-ranges')
@login_required
def color_ranges_get():
    from libs.color_ranges import view
    try:
        return jsonify(view(Executer.instance.device_executer._config))
    except (ValueError, OSError, TypeError) as exc:
        return jsonify(error=str(exc)), 400


@device_api.post('/api/system/color-ranges')
@login_required
def color_ranges_save():
    from libs.color_ranges import save
    data=request.get_json(silent=True)
    if not isinstance(data,dict) or set(data)!={'device','ranges'}:
        return jsonify(error='Choose an output and its RGB color-order ranges'),400
    try:
        rows=save(data['device'],data['ranges'],Executer.instance.device_executer._config)
        return jsonify(ok=True,ranges=rows)
    except (ValueError, OSError, TypeError) as exc:
        return jsonify(error=str(exc)),400
