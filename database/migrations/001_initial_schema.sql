-- VibeX19 initial database schema
-- Generated from SQLAlchemy models via tools/export_schema.py
-- Target: PostgreSQL (Supabase)
-- Tables: 66

CREATE TABLE admin_permissions (
	id BIGSERIAL NOT NULL, 
	userid BIGINT NOT NULL, 
	permission VARCHAR(128) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (id)
);
CREATE INDEX ix_admin_permissions_permission ON admin_permissions (permission);
CREATE INDEX ix_admin_permissions_userid ON admin_permissions (userid);
CREATE TABLE asset (
	id BIGSERIAL NOT NULL, 
	roblox_asset_id BIGINT, 
	name TEXT NOT NULL, 
	description VARCHAR(4096) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	asset_type assettype NOT NULL, 
	asset_genre SMALLINT NOT NULL, 
	creator_type SMALLINT NOT NULL, 
	creator_id BIGINT NOT NULL, 
	moderation_status SMALLINT NOT NULL, 
	is_for_sale BOOLEAN NOT NULL, 
	price_robux BIGINT NOT NULL, 
	price_tix BIGINT NOT NULL, 
	is_limited BOOLEAN NOT NULL, 
	is_limited_unique BOOLEAN NOT NULL, 
	serial_count BIGINT NOT NULL, 
	sale_count BIGINT NOT NULL, 
	offsale_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (id)
);
CREATE INDEX ix_asset_creator_id ON asset (creator_id);
CREATE INDEX ix_asset_moderation_status ON asset (moderation_status);
CREATE INDEX ix_asset_is_limited ON asset (is_limited);
CREATE INDEX ix_asset_is_for_sale ON asset (is_for_sale);
CREATE INDEX ix_asset_asset_type ON asset (asset_type);
CREATE INDEX ix_asset_roblox_asset_id ON asset (roblox_asset_id);
CREATE TABLE asset_favorite (
	id BIGSERIAL NOT NULL, 
	assetid BIGINT NOT NULL, 
	userid BIGINT NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_asset_favorite_assetid ON asset_favorite (assetid);
CREATE INDEX ix_asset_favorite_userid ON asset_favorite (userid);
CREATE TABLE asset_rap (
	assetid BIGSERIAL NOT NULL, 
	rap BIGINT NOT NULL, 
	updated TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (assetid), 
	UNIQUE (assetid)
);
CREATE TABLE asset_vote (
	id BIGSERIAL NOT NULL, 
	assetid BIGINT NOT NULL, 
	userid BIGINT NOT NULL, 
	vote BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_asset_vote_userid ON asset_vote (userid);
CREATE INDEX ix_asset_vote_assetid ON asset_vote (assetid);
CREATE TABLE fflag_group (
	group_id BIGSERIAL NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	description VARCHAR(512) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	apikey VARCHAR(128), 
	gameserver_only BOOLEAN NOT NULL, 
	PRIMARY KEY (group_id)
);
CREATE INDEX ix_fflag_group_group_id ON fflag_group (group_id);
CREATE TABLE fflag_value (
	flag_id BIGSERIAL NOT NULL, 
	group_id BIGINT NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	flag_type INTEGER NOT NULL, 
	flag_value TEXT NOT NULL, 
	PRIMARY KEY (flag_id)
);
CREATE INDEX ix_fflag_value_group_id ON fflag_value (group_id);
CREATE TABLE follow_relationship (
	id BIGSERIAL NOT NULL, 
	"followerUserId" BIGINT NOT NULL, 
	"followeeUserId" BIGINT NOT NULL, 
	created TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (id)
);
CREATE INDEX "ix_follow_relationship_followerUserId" ON follow_relationship ("followerUserId");
CREATE INDEX "ix_follow_relationship_followeeUserId" ON follow_relationship ("followeeUserId");
CREATE TABLE friend_relationship (
	id BIGSERIAL NOT NULL, 
	user_id BIGINT NOT NULL, 
	friend_id BIGINT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_friend_relationship_friend_id ON friend_relationship (friend_id);
CREATE INDEX ix_friend_relationship_user_id ON friend_relationship (user_id);
CREATE TABLE game_server (
	"serverId" UUID NOT NULL, 
	"serverName" VARCHAR(128) NOT NULL, 
	"serverIP" VARCHAR(128) NOT NULL, 
	"serverPort" INTEGER NOT NULL, 
	"accessKey" VARCHAR(128) NOT NULL, 
	"lastHeartbeat" TIMESTAMP WITHOUT TIME ZONE, 
	"heartbeatResponseTime" FLOAT, 
	"isRCCOnline" BOOLEAN NOT NULL, 
	"thumbnailQueueSize" INTEGER NOT NULL, 
	"RCCmemoryUsage" BIGINT NOT NULL, 
	"allowThumbnailGen" BOOLEAN NOT NULL, 
	"allowGameServerHost" BOOLEAN NOT NULL, 
	PRIMARY KEY ("serverId"), 
	UNIQUE ("serverId")
);
CREATE TABLE giftcard_key (
	id BIGSERIAL NOT NULL, 
	key VARCHAR(255) NOT NULL, 
	type giftcardtype NOT NULL, 
	value BIGINT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	redeemed_at TIMESTAMP WITHOUT TIME ZONE, 
	redeemed_by BIGINT, 
	PRIMARY KEY (id)
);
CREATE TABLE kofi_transaction (
	kofi_transaction_id TEXT NOT NULL, 
	timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	donation_type TEXT NOT NULL, 
	amount FLOAT NOT NULL, 
	currency TEXT NOT NULL, 
	is_subscription_payment BOOLEAN NOT NULL, 
	message TEXT NOT NULL, 
	from_name TEXT NOT NULL, 
	from_email TEXT NOT NULL, 
	assigned_key TEXT, 
	PRIMARY KEY (kofi_transaction_id)
);
CREATE TABLE limited_item_transfer (
	id BIGSERIAL NOT NULL, 
	original_owner_id BIGINT NOT NULL, 
	new_owner_id BIGINT NOT NULL, 
	asset_id BIGINT NOT NULL, 
	user_asset_id BIGINT NOT NULL, 
	transferred_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	transfer_method limiteditemtransfermethod NOT NULL, 
	purchased_price BIGINT, 
	associated_trade_id BIGINT, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_limited_item_transfer_new_owner_id ON limited_item_transfer (new_owner_id);
CREATE INDEX ix_limited_item_transfer_asset_id ON limited_item_transfer (asset_id);
CREATE INDEX ix_limited_item_transfer_original_owner_id ON limited_item_transfer (original_owner_id);
CREATE INDEX ix_limited_item_transfer_user_asset_id ON limited_item_transfer (user_asset_id);
CREATE INDEX ix_limited_item_transfer_transfer_method ON limited_item_transfer (transfer_method);
CREATE TABLE package_asset (
	id BIGSERIAL NOT NULL, 
	package_asset_id BIGINT NOT NULL, 
	asset_id BIGINT NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_package_asset_package_asset_id ON package_asset (package_asset_id);
CREATE TABLE place_server (
	serveruuid UUID NOT NULL, 
	"originServerId" UUID NOT NULL, 
	"serverIP" VARCHAR(128) NOT NULL, 
	"serverPort" INTEGER NOT NULL, 
	"serverPlaceId" BIGINT NOT NULL, 
	"serverRunningTime" BIGINT NOT NULL, 
	"playerCount" INTEGER NOT NULL, 
	"maxPlayerCount" INTEGER NOT NULL, 
	lastping TIMESTAMP WITHOUT TIME ZONE, 
	"reservedServerAccessCode" TEXT, 
	PRIMARY KEY (serveruuid), 
	UNIQUE (serveruuid)
);
CREATE INDEX "ix_place_server_originServerId" ON place_server ("originServerId");
CREATE INDEX "ix_place_server_serverPlaceId" ON place_server ("serverPlaceId");
CREATE TABLE points_service (
	id BIGSERIAL NOT NULL, 
	"placeId" BIGINT NOT NULL, 
	"userId" BIGINT NOT NULL, 
	points BIGINT NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX "ix_points_service_placeId" ON points_service ("placeId");
CREATE INDEX "ix_points_service_userId" ON points_service ("userId");
CREATE TABLE previously_played (
	id BIGSERIAL NOT NULL, 
	userid BIGINT NOT NULL, 
	lastplayed TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	placeid BIGINT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (id)
);
CREATE INDEX ix_previously_played_placeid ON previously_played (placeid);
CREATE INDEX ix_previously_played_userid ON previously_played (userid);
CREATE TABLE universe (
	id BIGSERIAL NOT NULL, 
	root_place_id BIGINT NOT NULL, 
	creator_id BIGINT NOT NULL, 
	creator_type SMALLINT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	place_rig_choice placerigchoice NOT NULL, 
	place_year placeyear NOT NULL, 
	is_featured BOOLEAN NOT NULL, 
	minimum_account_age INTEGER NOT NULL, 
	bc_required BOOLEAN NOT NULL, 
	allow_direct_join BOOLEAN NOT NULL, 
	is_public BOOLEAN NOT NULL, 
	moderation_status SMALLINT NOT NULL, 
	visit_count BIGINT NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_universe_moderation_status ON universe (moderation_status);
CREATE INDEX ix_universe_allow_direct_join ON universe (allow_direct_join);
CREATE INDEX ix_universe_is_public ON universe (is_public);
CREATE INDEX ix_universe_creator_id ON universe (creator_id);
CREATE INDEX ix_universe_bc_required ON universe (bc_required);
CREATE INDEX ix_universe_visit_count ON universe (visit_count);
CREATE UNIQUE INDEX ix_universe_root_place_id ON universe (root_place_id);
CREATE INDEX ix_universe_is_featured ON universe (is_featured);
CREATE TABLE "user" (
	id BIGSERIAL NOT NULL, 
	username TEXT NOT NULL, 
	password TEXT NOT NULL, 
	created TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	description TEXT NOT NULL, 
	lastonline TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	accountstatus INTEGER NOT NULL, 
	"TOTPEnabled" BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (id)
);
CREATE UNIQUE INDEX ix_user_username ON "user" (username);
CREATE TABLE user_avatar (
	user_id BIGSERIAL NOT NULL, 
	content_hash VARCHAR(512), 
	avatar_type SMALLINT NOT NULL, 
	head_color_id BIGINT NOT NULL, 
	torso_color_id BIGINT NOT NULL, 
	right_arm_color_id BIGINT NOT NULL, 
	left_arm_color_id BIGINT NOT NULL, 
	right_leg_color_id BIGINT NOT NULL, 
	left_leg_color_id BIGINT NOT NULL, 
	r15 BOOLEAN, 
	height_scale FLOAT NOT NULL, 
	width_scale FLOAT NOT NULL, 
	head_scale FLOAT NOT NULL, 
	proportion_scale FLOAT NOT NULL, 
	body_type_scale FLOAT NOT NULL, 
	PRIMARY KEY (user_id), 
	UNIQUE (user_id)
);
CREATE TABLE user_thumbnail (
	userid BIGSERIAL NOT NULL, 
	full_contenthash VARCHAR(512), 
	headshot_contenthash VARCHAR(512), 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (userid), 
	UNIQUE (userid)
);
CREATE TABLE user_trade (
	id BIGSERIAL NOT NULL, 
	sender_userid BIGINT NOT NULL, 
	recipient_userid BIGINT NOT NULL, 
	sender_userid_robux BIGINT NOT NULL, 
	recipient_userid_robux BIGINT NOT NULL, 
	status tradestatus NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_user_trade_recipient_userid ON user_trade (recipient_userid);
CREATE INDEX ix_user_trade_sender_userid ON user_trade (sender_userid);
CREATE TABLE user_transaction (
	id BIGSERIAL NOT NULL, 
	reciever_id BIGINT NOT NULL, 
	reciever_type INTEGER NOT NULL, 
	sender_id BIGINT NOT NULL, 
	sender_type INTEGER NOT NULL, 
	currency_amount BIGINT NOT NULL, 
	currency_type INTEGER NOT NULL, 
	"assetId" BIGINT, 
	custom_text TEXT, 
	transaction_type transactiontype NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_user_transaction_transaction_type ON user_transaction (transaction_type);
CREATE INDEX ix_user_transaction_sender_id ON user_transaction (sender_id);
CREATE INDEX "ix_user_transaction_assetId" ON user_transaction ("assetId");
CREATE INDEX ix_user_transaction_reciever_id ON user_transaction (reciever_id);
CREATE TABLE asset_moderation_link (
	id BIGSERIAL NOT NULL, 
	"ParentAssetId" BIGINT NOT NULL, 
	"ChildAssetId" BIGINT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (id), 
	FOREIGN KEY("ParentAssetId") REFERENCES asset (id), 
	FOREIGN KEY("ChildAssetId") REFERENCES asset (id)
);
CREATE INDEX "ix_asset_moderation_link_ParentAssetId" ON asset_moderation_link ("ParentAssetId");
CREATE INDEX "ix_asset_moderation_link_ChildAssetId" ON asset_moderation_link ("ChildAssetId");
CREATE TABLE asset_thumbnail (
	id BIGSERIAL NOT NULL, 
	asset_id BIGINT NOT NULL, 
	asset_version_id BIGINT NOT NULL, 
	content_hash VARCHAR(512) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	moderation_status SMALLINT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (id), 
	FOREIGN KEY(asset_id) REFERENCES asset (id)
);
CREATE INDEX ix_asset_thumbnail_asset_id ON asset_thumbnail (asset_id);
CREATE TABLE asset_version (
	id BIGSERIAL NOT NULL, 
	asset_id BIGINT NOT NULL, 
	version BIGINT NOT NULL, 
	content_hash VARCHAR(512) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	uploaded_by BIGINT, 
	PRIMARY KEY (id), 
	UNIQUE (id), 
	FOREIGN KEY(uploaded_by) REFERENCES "user" (id)
);
CREATE INDEX ix_asset_version_asset_id ON asset_version (asset_id);
CREATE INDEX ix_asset_version_uploaded_by ON asset_version (uploaded_by);
CREATE TABLE cryptomus_invoice (
	id TEXT NOT NULL, 
	cryptomus_invoice_id TEXT NOT NULL, 
	initiator_id INTEGER NOT NULL, 
	required_amount FLOAT NOT NULL, 
	paid_amount_usd FLOAT NOT NULL, 
	currency TEXT NOT NULL, 
	status cryptomuspaymentstatus NOT NULL, 
	is_final BOOLEAN NOT NULL, 
	extra_data TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	assigned_key TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(initiator_id) REFERENCES "user" (id)
);
CREATE INDEX ix_cryptomus_invoice_cryptomus_invoice_id ON cryptomus_invoice (cryptomus_invoice_id);
CREATE UNIQUE INDEX ix_cryptomus_invoice_id ON cryptomus_invoice (id);
CREATE INDEX ix_cryptomus_invoice_initiator_id ON cryptomus_invoice (initiator_id);
CREATE TABLE exchange_offer (
	id BIGSERIAL NOT NULL, 
	creator_id BIGINT NOT NULL, 
	offer_value BIGINT NOT NULL, 
	receive_value BIGINT NOT NULL, 
	offer_currency_type SMALLINT NOT NULL, 
	reciever_id BIGINT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	ratio FLOAT NOT NULL, 
	worth FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(creator_id) REFERENCES "user" (id), 
	FOREIGN KEY(reciever_id) REFERENCES "user" (id)
);
CREATE INDEX ix_exchange_offer_worth ON exchange_offer (worth);
CREATE INDEX ix_exchange_offer_reciever_id ON exchange_offer (reciever_id);
CREATE INDEX ix_exchange_offer_creator_id ON exchange_offer (creator_id);
CREATE TABLE friend_request (
	id BIGSERIAL NOT NULL, 
	requester_id BIGINT NOT NULL, 
	requestee_id BIGINT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(requester_id) REFERENCES "user" (id)
);
CREATE INDEX ix_friend_request_requester_id ON friend_request (requester_id);
CREATE INDEX ix_friend_request_requestee_id ON friend_request (requestee_id);
CREATE TABLE game_session_log (
	id BIGSERIAL NOT NULL, 
	user_id BIGINT NOT NULL, 
	serveruuid UUID NOT NULL, 
	joined_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	left_at TIMESTAMP WITHOUT TIME ZONE, 
	place_id BIGINT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);
CREATE INDEX ix_game_session_log_user_id ON game_session_log (user_id);
CREATE INDEX ix_game_session_log_joined_at ON game_session_log (joined_at);
CREATE INDEX ix_game_session_log_serveruuid ON game_session_log (serveruuid);
CREATE INDEX ix_game_session_log_place_id ON game_session_log (place_id);
CREATE TABLE gamepass_link (
	gamepass_id BIGINT NOT NULL, 
	place_id BIGINT NOT NULL, 
	creator_id BIGINT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	universe_id BIGINT, 
	PRIMARY KEY (gamepass_id, place_id), 
	FOREIGN KEY(gamepass_id) REFERENCES asset (id), 
	FOREIGN KEY(place_id) REFERENCES asset (id), 
	FOREIGN KEY(creator_id) REFERENCES "user" (id), 
	FOREIGN KEY(universe_id) REFERENCES universe (id)
);
CREATE INDEX ix_gamepass_link_universe_id ON gamepass_link (universe_id);
CREATE INDEX ix_gamepass_link_place_id ON gamepass_link (place_id);
CREATE INDEX ix_gamepass_link_creator_id ON gamepass_link (creator_id);
CREATE TABLE "group" (
	id BIGSERIAL NOT NULL, 
	owner_id BIGINT, 
	name VARCHAR(255) NOT NULL, 
	description VARCHAR(1024) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	locked BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(owner_id) REFERENCES "user" (id)
);
CREATE INDEX ix_group_name ON "group" (name);
CREATE INDEX ix_group_owner_id ON "group" (owner_id);
CREATE TABLE invite_key (
	id BIGSERIAL NOT NULL, 
	key VARCHAR(255) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	created_by BIGINT, 
	used_by BIGINT, 
	used_on TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by) REFERENCES "user" (id), 
	FOREIGN KEY(used_by) REFERENCES "user" (id)
);
CREATE INDEX ix_invite_key_created_by ON invite_key (created_by);
CREATE TABLE legacy_data_persistence (
	id BIGSERIAL NOT NULL, 
	userid BIGINT NOT NULL, 
	placeid BIGINT NOT NULL, 
	data BYTEA NOT NULL, 
	last_updated TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	universe_id BIGINT, 
	PRIMARY KEY (id), 
	UNIQUE (id), 
	FOREIGN KEY(universe_id) REFERENCES universe (id)
);
CREATE INDEX ix_legacy_data_persistence_universe_id ON legacy_data_persistence (universe_id);
CREATE INDEX ix_legacy_data_persistence_userid ON legacy_data_persistence (userid);
CREATE INDEX ix_legacy_data_persistence_placeid ON legacy_data_persistence (placeid);
CREATE TABLE linked_discord (
	user_id BIGINT NOT NULL, 
	discord_id BIGINT NOT NULL, 
	discord_username VARCHAR(255) NOT NULL, 
	discord_discriminator VARCHAR(255), 
	discord_avatar TEXT, 
	discord_access_token VARCHAR(512), 
	discord_refresh_token VARCHAR(512), 
	discord_expiry TIMESTAMP WITHOUT TIME ZONE, 
	last_updated TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	linked_on TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (user_id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);
CREATE TABLE login_record (
	id BIGSERIAL NOT NULL, 
	userid BIGINT NOT NULL, 
	ip TEXT NOT NULL, 
	useragent TEXT NOT NULL, 
	timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	session_token TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(userid) REFERENCES "user" (id)
);
CREATE INDEX ix_login_record_session_token ON login_record (session_token);
CREATE INDEX ix_login_record_ip ON login_record (ip);
CREATE INDEX ix_login_record_userid ON login_record (userid);
CREATE TABLE message (
	id BIGSERIAL NOT NULL, 
	sender_id BIGINT NOT NULL, 
	recipient_id BIGINT NOT NULL, 
	created TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	read BOOLEAN NOT NULL, 
	subject VARCHAR(128) NOT NULL, 
	content TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sender_id) REFERENCES "user" (id), 
	FOREIGN KEY(recipient_id) REFERENCES "user" (id)
);
CREATE INDEX ix_message_sender_id ON message (sender_id);
CREATE INDEX ix_message_recipient_id ON message (recipient_id);
CREATE TABLE past_username (
	id BIGSERIAL NOT NULL, 
	user_id BIGINT NOT NULL, 
	username TEXT NOT NULL, 
	created TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);
CREATE INDEX ix_past_username_user_id ON past_username (user_id);
CREATE TABLE place (
	placeid BIGINT NOT NULL, 
	visitcount BIGINT NOT NULL, 
	is_public BOOLEAN NOT NULL, 
	maxplayers BIGINT NOT NULL, 
	placeyear placeyear NOT NULL, 
	featured BOOLEAN NOT NULL, 
	bc_required BOOLEAN NOT NULL, 
	rig_choice placerigchoice NOT NULL, 
	chat_style chatstyle NOT NULL, 
	min_account_age INTEGER NOT NULL, 
	parent_universe_id BIGINT, 
	PRIMARY KEY (placeid), 
	UNIQUE (placeid), 
	FOREIGN KEY(placeid) REFERENCES asset (id), 
	FOREIGN KEY(parent_universe_id) REFERENCES universe (id)
);
CREATE INDEX ix_place_parent_universe_id ON place (parent_universe_id);
CREATE INDEX ix_place_bc_required ON place (bc_required);
CREATE INDEX ix_place_featured ON place (featured);
CREATE TABLE place_datastore (
	id BIGSERIAL NOT NULL, 
	placeid BIGINT NOT NULL, 
	scope VARCHAR(255) NOT NULL, 
	key VARCHAR(255) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	value VARCHAR(1048576) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	universe_id BIGINT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(universe_id) REFERENCES universe (id)
);
CREATE INDEX ix_place_datastore_placeid ON place_datastore (placeid);
CREATE INDEX ix_place_datastore_universe_id ON place_datastore (universe_id);
CREATE INDEX ix_place_datastore_scope ON place_datastore (scope);
CREATE INDEX ix_place_datastore_key ON place_datastore (key);
CREATE TABLE place_icon (
	placeid BIGINT NOT NULL, 
	contenthash VARCHAR(512), 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	moderation_status SMALLINT NOT NULL, 
	PRIMARY KEY (placeid), 
	UNIQUE (placeid), 
	FOREIGN KEY(placeid) REFERENCES asset (id)
);
CREATE TABLE place_ordered_datastore (
	id BIGSERIAL NOT NULL, 
	placeid BIGINT NOT NULL, 
	scope VARCHAR(255) NOT NULL, 
	key VARCHAR(255) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	value BIGINT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	universe_id BIGINT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(universe_id) REFERENCES universe (id)
);
CREATE INDEX ix_place_ordered_datastore_universe_id ON place_ordered_datastore (universe_id);
CREATE TABLE place_server_player (
	userid BIGINT NOT NULL, 
	serveruuid UUID NOT NULL, 
	"joinTime" TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	"lastHeartbeat" TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (userid), 
	UNIQUE (userid), 
	FOREIGN KEY(userid) REFERENCES "user" (id)
);
CREATE INDEX ix_place_server_player_serveruuid ON place_server_player (serveruuid);
CREATE TABLE user_asset (
	id BIGSERIAL NOT NULL, 
	userid BIGINT NOT NULL, 
	assetid BIGINT NOT NULL, 
	serial BIGINT, 
	price BIGINT NOT NULL, 
	created TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_for_sale BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (id), 
	FOREIGN KEY(assetid) REFERENCES asset (id)
);
CREATE INDEX ix_user_asset_assetid ON user_asset (assetid);
CREATE INDEX ix_user_asset_userid ON user_asset (userid);
CREATE TABLE user_avatar_asset (
	id BIGSERIAL NOT NULL, 
	user_id BIGINT NOT NULL, 
	asset_id BIGINT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(asset_id) REFERENCES asset (id)
);
CREATE INDEX ix_user_avatar_asset_user_id ON user_avatar_asset (user_id);
CREATE INDEX ix_user_avatar_asset_asset_id ON user_avatar_asset (asset_id);
CREATE TABLE user_ban (
	id BIGSERIAL NOT NULL, 
	userid BIGINT NOT NULL, 
	author_userid BIGINT NOT NULL, 
	reason VARCHAR(512) NOT NULL, 
	ban_type bantype NOT NULL, 
	moderator_note VARCHAR(512), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE, 
	acknowledged BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(userid) REFERENCES "user" (id), 
	FOREIGN KEY(author_userid) REFERENCES "user" (id)
);
CREATE TABLE user_economy (
	userid INTEGER NOT NULL, 
	robux INTEGER NOT NULL, 
	tix INTEGER NOT NULL, 
	PRIMARY KEY (userid), 
	UNIQUE (userid), 
	FOREIGN KEY(userid) REFERENCES "user" (id)
);
CREATE TABLE user_email (
	user_id BIGINT NOT NULL, 
	email VARCHAR(256) NOT NULL, 
	verified BOOLEAN NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (user_id, email), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);
CREATE TABLE user_hwid_log (
	id BIGSERIAL NOT NULL, 
	user_id BIGINT NOT NULL, 
	hwid TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);
CREATE INDEX ix_user_hwid_log_user_id ON user_hwid_log (user_id);
CREATE INDEX ix_user_hwid_log_hwid ON user_hwid_log (hwid);
CREATE TABLE user_membership (
	user_id BIGINT NOT NULL, 
	membership_type membershiptype NOT NULL, 
	created TIMESTAMP WITHOUT TIME ZONE, 
	expiration TIMESTAMP WITHOUT TIME ZONE, 
	next_stipend TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (user_id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);
CREATE TABLE developer_product (
	productid BIGSERIAL NOT NULL, 
	placeid BIGINT, 
	name VARCHAR(256) NOT NULL, 
	description VARCHAR(1024) NOT NULL, 
	iconimage_assetid BIGINT, 
	robux_price BIGINT NOT NULL, 
	sales_count BIGINT NOT NULL, 
	is_for_sale BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	creator_id BIGINT NOT NULL, 
	universe_id BIGINT, 
	PRIMARY KEY (productid), 
	UNIQUE (productid), 
	FOREIGN KEY(placeid) REFERENCES place (placeid), 
	FOREIGN KEY(iconimage_assetid) REFERENCES asset (id), 
	FOREIGN KEY(creator_id) REFERENCES "user" (id), 
	FOREIGN KEY(universe_id) REFERENCES universe (id)
);
CREATE INDEX ix_developer_product_placeid ON developer_product (placeid);
CREATE INDEX ix_developer_product_creator_id ON developer_product (creator_id);
CREATE INDEX ix_developer_product_universe_id ON developer_product (universe_id);
CREATE INDEX ix_developer_product_iconimage_assetid ON developer_product (iconimage_assetid);
CREATE TABLE group_economy (
	group_id BIGINT NOT NULL, 
	robux_balance BIGINT NOT NULL, 
	tix_balance BIGINT NOT NULL, 
	PRIMARY KEY (group_id), 
	FOREIGN KEY(group_id) REFERENCES "group" (id)
);
CREATE TABLE group_icon (
	group_id BIGINT NOT NULL, 
	content_hash VARCHAR(512) NOT NULL, 
	moderation_status INTEGER NOT NULL, 
	creator_id BIGINT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (group_id), 
	FOREIGN KEY(group_id) REFERENCES "group" (id), 
	FOREIGN KEY(creator_id) REFERENCES "user" (id)
);
CREATE INDEX ix_group_icon_creator_id ON group_icon (creator_id);
CREATE INDEX ix_group_icon_content_hash ON group_icon (content_hash);
CREATE TABLE group_join_request (
	id BIGSERIAL NOT NULL, 
	group_id BIGINT NOT NULL, 
	user_id BIGINT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(group_id) REFERENCES "group" (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);
CREATE INDEX ix_group_join_request_user_id ON group_join_request (user_id);
CREATE INDEX ix_group_join_request_group_id ON group_join_request (group_id);
CREATE TABLE group_role (
	id BIGSERIAL NOT NULL, 
	group_id BIGINT NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	description VARCHAR(255) NOT NULL, 
	rank INTEGER NOT NULL, 
	member_count INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(group_id) REFERENCES "group" (id)
);
CREATE INDEX ix_group_role_group_id ON group_role (group_id);
CREATE TABLE group_settings (
	group_id BIGINT NOT NULL, 
	approval_required BOOLEAN NOT NULL, 
	enemies_allowed BOOLEAN NOT NULL, 
	funds_visible BOOLEAN NOT NULL, 
	games_visible BOOLEAN NOT NULL, 
	membership_required BOOLEAN NOT NULL, 
	last_updated TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (group_id), 
	FOREIGN KEY(group_id) REFERENCES "group" (id)
);
CREATE TABLE group_status (
	id BIGSERIAL NOT NULL, 
	group_id BIGINT NOT NULL, 
	poster_id BIGINT NOT NULL, 
	content VARCHAR(1024) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(group_id) REFERENCES "group" (id), 
	FOREIGN KEY(poster_id) REFERENCES "user" (id)
);
CREATE INDEX ix_group_status_group_id ON group_status (group_id);
CREATE INDEX ix_group_status_poster_id ON group_status (poster_id);
CREATE TABLE group_wall_post (
	id BIGSERIAL NOT NULL, 
	group_id BIGINT NOT NULL, 
	poster_id BIGINT NOT NULL, 
	content VARCHAR(1024) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(group_id) REFERENCES "group" (id), 
	FOREIGN KEY(poster_id) REFERENCES "user" (id)
);
CREATE INDEX ix_group_wall_post_group_id ON group_wall_post (group_id);
CREATE INDEX ix_group_wall_post_poster_id ON group_wall_post (poster_id);
CREATE TABLE moderator_note (
	id BIGSERIAL NOT NULL, 
	user_id BIGINT, 
	note_creator_id BIGINT, 
	note TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	related_action_id BIGINT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id), 
	FOREIGN KEY(note_creator_id) REFERENCES "user" (id), 
	FOREIGN KEY(related_action_id) REFERENCES user_ban (id)
);
CREATE INDEX ix_moderator_note_created_at ON moderator_note (created_at);
CREATE INDEX ix_moderator_note_related_action_id ON moderator_note (related_action_id);
CREATE INDEX ix_moderator_note_updated_at ON moderator_note (updated_at);
CREATE INDEX ix_moderator_note_note_creator_id ON moderator_note (note_creator_id);
CREATE INDEX ix_moderator_note_user_id ON moderator_note (user_id);
CREATE TABLE place_badge (
	id BIGSERIAL NOT NULL, 
	associated_place_id BIGINT, 
	icon_image_id BIGINT NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	description VARCHAR(1024) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	asset_reward BIGINT, 
	universe_id BIGINT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(associated_place_id) REFERENCES place (placeid), 
	FOREIGN KEY(icon_image_id) REFERENCES asset (id), 
	FOREIGN KEY(universe_id) REFERENCES universe (id)
);
CREATE INDEX ix_place_badge_updated_at ON place_badge (updated_at);
CREATE INDEX ix_place_badge_associated_place_id ON place_badge (associated_place_id);
CREATE INDEX ix_place_badge_universe_id ON place_badge (universe_id);
CREATE INDEX ix_place_badge_created_at ON place_badge (created_at);
CREATE TABLE user_trade_item (
	id BIGSERIAL NOT NULL, 
	tradeid BIGINT NOT NULL, 
	userid BIGINT NOT NULL, 
	user_asset_id BIGINT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_asset_id) REFERENCES user_asset (id)
);
CREATE INDEX ix_user_trade_item_userid ON user_trade_item (userid);
CREATE INDEX ix_user_trade_item_tradeid ON user_trade_item (tradeid);
CREATE TABLE group_member (
	id BIGSERIAL NOT NULL, 
	group_id BIGINT NOT NULL, 
	user_id BIGINT NOT NULL, 
	group_role_id BIGINT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(group_id) REFERENCES "group" (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id), 
	FOREIGN KEY(group_role_id) REFERENCES group_role (id)
);
CREATE INDEX ix_group_member_user_id ON group_member (user_id);
CREATE INDEX ix_group_member_group_id ON group_member (group_id);
CREATE INDEX ix_group_member_group_role_id ON group_member (group_role_id);
CREATE TABLE group_role_permission (
	group_role_id BIGINT NOT NULL, 
	delete_from_wall BOOLEAN NOT NULL, 
	post_to_wall BOOLEAN NOT NULL, 
	invite_members BOOLEAN NOT NULL, 
	post_to_status BOOLEAN NOT NULL, 
	remove_members BOOLEAN NOT NULL, 
	view_status BOOLEAN NOT NULL, 
	view_wall BOOLEAN NOT NULL, 
	change_rank BOOLEAN NOT NULL, 
	advertise_group BOOLEAN NOT NULL, 
	manage_relationships BOOLEAN NOT NULL, 
	add_group_places BOOLEAN NOT NULL, 
	view_audit_logs BOOLEAN NOT NULL, 
	create_items BOOLEAN NOT NULL, 
	manage_items BOOLEAN NOT NULL, 
	spend_group_funds BOOLEAN NOT NULL, 
	manage_clan BOOLEAN NOT NULL, 
	manage_group_games BOOLEAN NOT NULL, 
	PRIMARY KEY (group_role_id), 
	FOREIGN KEY(group_role_id) REFERENCES group_role (id)
);
CREATE TABLE moderator_note_attachment (
	id BIGSERIAL NOT NULL, 
	moderator_note_id BIGINT, 
	attachment_hash VARCHAR(512) NOT NULL, 
	attachment_name VARCHAR(512) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(moderator_note_id) REFERENCES moderator_note (id)
);
CREATE INDEX ix_moderator_note_attachment_attachment_name ON moderator_note_attachment (attachment_name);
CREATE INDEX ix_moderator_note_attachment_attachment_hash ON moderator_note_attachment (attachment_hash);
CREATE INDEX ix_moderator_note_attachment_moderator_note_id ON moderator_note_attachment (moderator_note_id);
CREATE TABLE product_receipt (
	receipt_id BIGSERIAL NOT NULL, 
	user_id BIGINT NOT NULL, 
	product_id BIGINT NOT NULL, 
	robux_amount BIGINT NOT NULL, 
	is_processed BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (receipt_id), 
	UNIQUE (receipt_id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id), 
	FOREIGN KEY(product_id) REFERENCES developer_product (productid)
);
CREATE INDEX ix_product_receipt_user_id ON product_receipt (user_id);
CREATE INDEX ix_product_receipt_product_id ON product_receipt (product_id);
CREATE TABLE user_badge (
	id BIGSERIAL NOT NULL, 
	badge_id BIGINT, 
	user_id BIGINT, 
	awarded_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(badge_id) REFERENCES place_badge (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);
CREATE INDEX ix_user_badge_user_id ON user_badge (user_id);
CREATE INDEX ix_user_badge_badge_id ON user_badge (badge_id);
CREATE INDEX ix_user_badge_awarded_at ON user_badge (awarded_at);
