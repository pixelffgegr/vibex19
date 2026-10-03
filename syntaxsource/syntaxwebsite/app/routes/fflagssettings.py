from flask import Blueprint, render_template, request, redirect, url_for, jsonify, make_response
from app.models.fflag_group import FflagGroup
from app.models.fflag_value import FflagValue
from app.models.gameservers import GameServer
from app.extensions import redis_controller, get_remote_address
import json
import base64
import logging

FFlagRoute = Blueprint("fflag", __name__, url_prefix="/")

def ClearCache( GroupId : int ):
    redis_controller.delete("fflags_" + str(GroupId))
    GenerateFFlags(GroupId, True)

def GenerateFFlags( GroupId : int, BypassCache : bool = False ) -> dict:
    if not BypassCache:
        CachedFFlags = redis_controller.get("fflags_" + str(GroupId))
        if CachedFFlags is not None:
            return json.loads(CachedFFlags)

    FFlagValues = FflagValue.query.filter_by(group_id=GroupId).all()
    if FFlagValues is None:
        return jsonify({}),200
    
    FinalData = {}
    for FFlagValue in FFlagValues:
        FinalData[FFlagValue.name] = str(base64.b64decode(FFlagValue.flag_value).decode('utf-8'))

    redis_controller.set("fflags_" + str(GroupId), json.dumps(FinalData), ex = 60 * 60)
    return FinalData

@FFlagRoute.route("/Setting/QuietGet/<group>", methods=["GET"])
@FFlagRoute.route("/Setting/QuietGet/<group>/", methods=["GET"])
@FFlagRoute.route("/Setting/Get/<group>/", methods=["GET"])
def get_fflag(group):
    # RCC/clients may request the group with or without the application_ prefix
    FFlagGroupObj : FflagGroup = FflagGroup.query.filter_by(name=group).first()
    if FFlagGroupObj is None:
        FFlagGroupObj = FflagGroup.query.filter_by(name="application_" + group).first()
    if FFlagGroupObj is None:
        return 'Invalid request',400

    # groups may optionally be locked to an apiKey (RCC passes ?apiKey=...)
    RequestingApiKey = request.args.get(key="apiKey", default=None, type=str)
    if FFlagGroupObj.apikey and RequestingApiKey != FFlagGroupObj.apikey:
        return 'Invalid request',400

    if FFlagGroupObj.gameserver_only:
        RequestingRemoteAddress = get_remote_address()
        GameServerObj = GameServer.query.filter_by( serverIP = RequestingRemoteAddress ).first()
        if GameServerObj is None:
            return 'Invalid request',400
    
    return jsonify(GenerateFFlags(FFlagGroupObj.group_id)),200

@FFlagRoute.route("/v1/settings/application", methods=["GET"])
def fflag_application():
    applicationName : str = request.args.get(key="applicationName", default=None, type=str)
    if applicationName is None:
        return 'Invalid request',400
    applicationName = "application_" + applicationName

    FFlagGroupObj : FflagGroup = FflagGroup.query.filter_by(name=applicationName).first()
    if FFlagGroupObj is None:
        # RCC builds do not all ask for their settings the same way:
        #   RCC2020 -> "RCCService<accesskey>"
        #   RCC2021 -> "6sxp8X2Y02<accesskey>"  (build id in front, no prefix)
        # Try shorter suffixes of the requested name against both the bare and
        # the RCCService-prefixed group so every build finds its settings.
        for cut in range(1, len(applicationName)):
            Suffix : str = applicationName[cut:]
            for CandidateName in ("application_" + Suffix, "application_RCCService" + Suffix):
                FFlagGroupObj = FflagGroup.query.filter_by(name=CandidateName).first()
                if FFlagGroupObj is not None:
                    logging.info(f"fflag_application: resolved {applicationName} to {CandidateName}")
                    break
            if FFlagGroupObj is not None:
                break
    if FFlagGroupObj is None:
        return 'Invalid request',400
    
    if FFlagGroupObj.gameserver_only:
        RequestingRemoteAddress = get_remote_address()
        GameServerObj = GameServer.query.filter_by( serverIP = RequestingRemoteAddress ).first()
        if GameServerObj is None:
            return 'Invalid request',400
    
    return jsonify({
        "applicationSettings": GenerateFFlags(FFlagGroupObj.group_id)
    }),200


@FFlagRoute.route("/v2/settings/application/<group>", methods=["GET"])
@FFlagRoute.route("/v2/settings/application/<group>/bucket/<bucket>", methods=["GET"])
def fflag_application_v2(group, bucket=None):
    """Per-group settings fetch used by RCC/clients after bootstrapping
    (clientsettings, avatar, inventory, ...). Same payload shape as v1."""
    FFlagGroupObj : FflagGroup = FflagGroup.query.filter_by(name="application_" + group).first()
    if FFlagGroupObj is None:
        return jsonify({"applicationSettings": {}}),200
    
    if FFlagGroupObj.gameserver_only:
        RequestingRemoteAddress = get_remote_address()
        GameServerObj = GameServer.query.filter_by( serverIP = RequestingRemoteAddress ).first()
        if GameServerObj is None:
            return 'Invalid request',400
    
    return jsonify({
        "applicationSettings": GenerateFFlags(FFlagGroupObj.group_id)
    }),200
    
