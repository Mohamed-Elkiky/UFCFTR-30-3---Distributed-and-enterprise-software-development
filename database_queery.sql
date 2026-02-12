CREATE TYPE "user_role" AS ENUM (
  'customer',
  'producer',
  'community_group',
  'restaurant',
  'admin'
);

CREATE TYPE "availability_status" AS ENUM (
  'in_season',
  'available_year_round',
  'out_of_season',
  'unavailable'
);

CREATE TYPE "order_status" AS ENUM (
  'pending',
  'confirmed',
  'ready',
  'delivered',
  'cancelled'
);

CREATE TYPE "payment_status" AS ENUM (
  'initiated',
  'authorised',
  'captured',
  'failed',
  'refunded'
);

CREATE TYPE "settlement_status" AS ENUM (
  'pending',
  'processed'
);

CREATE TYPE "notification_channel" AS ENUM (
  'in_app',
  'email'
);

CREATE TYPE "notification_type" AS ENUM (
  'order_status',
  'low_stock',
  'surplus_deal',
  'recurring_order',
  'system'
);

CREATE TABLE "product_category" (
  "id" bigserial PRIMARY KEY,
  "name" text UNIQUE NOT NULL,
  "created_at" timestamptz
);

CREATE TABLE "app_user" (
  "id" uuid PRIMARY KEY,
  "role" user_role NOT NULL,
  "email" text UNIQUE NOT NULL,
  "phone" text,
  "password_hash" text NOT NULL,
  "is_active" boolean,
  "created_at" timestamptz,
  "updated_at" timestamptz
);

CREATE TABLE "address" (
  "id" uuid PRIMARY KEY,
  "line1" text NOT NULL,
  "line2" text,
  "city" text,
  "postcode" text NOT NULL,
  "created_at" timestamptz
);

CREATE TABLE "producer_profile" (
  "user_id" uuid PRIMARY KEY,
  "business_name" text,
  "contact_name" text,
  "business_address_id" uuid,
  "is_verified" boolean,
  "min_lead_hours" integer,
  "created_at" timestamptz
);

CREATE TABLE "customer_profile" (
  "user_id" uuid PRIMARY KEY,
  "full_name" text,
  "delivery_address_id" uuid,
  "org_name" text,
  "org_type" text,
  "created_at" timestamptz
);

CREATE TABLE "product" (
  "id" uuid PRIMARY KEY,
  "producer_id" uuid,
  "category_id" bigint,
  "name" text,
  "description" text,
  "price_pence" integer,
  "unit" text,
  "availability" availability_status,
  "seasonal_start_month" smallint,
  "seasonal_end_month" smallint,
  "stock_qty" integer,
  "low_stock_threshold" integer,
  "organic_certified" boolean,
  "harvest_date" date,
  "best_before_date" date,
  "created_at" timestamptz,
  "updated_at" timestamptz
);

CREATE TABLE "allergen" (
  "id" bigserial PRIMARY KEY,
  "name" text UNIQUE
);

CREATE TABLE "product_allergen" (
  "product_id" uuid,
  "allergen_id" bigint,
  PRIMARY KEY ("product_id", "allergen_id")
);

CREATE TABLE "product_image" (
  "id" uuid PRIMARY KEY,
  "product_id" uuid,
  "url" text,
  "created_at" timestamptz
);

CREATE TABLE "surplus_deal" (
  "id" uuid PRIMARY KEY,
  "product_id" uuid UNIQUE,
  "discount_bp" integer,
  "expires_at" timestamptz,
  "note" text,
  "created_at" timestamptz
);

CREATE TABLE "cart" (
  "id" uuid PRIMARY KEY,
  "customer_id" uuid UNIQUE,
  "created_at" timestamptz,
  "updated_at" timestamptz
);

CREATE TABLE "cart_item" (
  "cart_id" uuid,
  "product_id" uuid,
  "quantity" integer,
  "added_at" timestamptz,
  PRIMARY KEY ("cart_id", "product_id")
);

CREATE TABLE "customer_order" (
  "id" uuid PRIMARY KEY,
  "customer_id" uuid,
  "delivery_address_id" uuid,
  "status" order_status,
  "placed_at" timestamptz,
  "total_gross_pence" integer,
  "commission_pence" integer,
  "total_net_pence" integer,
  "currency" text,
  "notes" text
);

CREATE TABLE "producer_order" (
  "id" uuid PRIMARY KEY,
  "customer_order_id" uuid,
  "producer_id" uuid,
  "delivery_date" date,
  "status" order_status,
  "status_updated_at" timestamptz,
  "subtotal_pence" integer,
  "producer_payout_pence" integer
);

CREATE TABLE "order_item" (
  "id" uuid PRIMARY KEY,
  "customer_order_id" uuid,
  "producer_order_id" uuid,
  "product_id" uuid,
  "product_name_snapshot" text,
  "unit_snapshot" text,
  "price_pence_snapshot" integer,
  "quantity" integer,
  "line_total_pence" integer,
  "created_at" timestamptz
);

CREATE TABLE "payment_transaction" (
  "id" uuid PRIMARY KEY,
  "customer_order_id" uuid UNIQUE,
  "provider" text,
  "provider_ref" text,
  "status" payment_status,
  "amount_pence" integer,
  "created_at" timestamptz,
  "updated_at" timestamptz
);

CREATE TABLE "commission_policy" (
  "id" bigserial PRIMARY KEY,
  "rate_bp" integer,
  "effective_from" timestamptz,
  "effective_to" timestamptz
);

CREATE TABLE "order_commission" (
  "customer_order_id" uuid PRIMARY KEY,
  "commission_policy_id" bigint,
  "rate_bp_snapshot" integer
);

CREATE TABLE "settlement_week" (
  "id" uuid PRIMARY KEY,
  "week_start" date,
  "week_end" date,
  "status" settlement_status,
  "created_at" timestamptz
);

CREATE TABLE "producer_settlement" (
  "id" uuid PRIMARY KEY,
  "settlement_week_id" uuid,
  "producer_id" uuid,
  "gross_pence" integer,
  "commission_pence" integer,
  "payout_pence" integer,
  "status" settlement_status,
  "processed_ref" text,
  "created_at" timestamptz
);

CREATE TABLE "producer_order_settlement_link" (
  "producer_order_id" uuid PRIMARY KEY,
  "producer_settlement_id" uuid
);

CREATE TABLE "product_review" (
  "id" uuid PRIMARY KEY,
  "product_id" uuid,
  "customer_id" uuid,
  "stars" smallint,
  "title" text,
  "body" text,
  "created_at" timestamptz
);

CREATE TABLE "recurring_order_template" (
  "id" uuid PRIMARY KEY,
  "customer_id" uuid,
  "name" text,
  "rrule" text,
  "active" boolean,
  "created_at" timestamptz
);

CREATE TABLE "recurring_order_item" (
  "template_id" uuid,
  "product_id" uuid,
  "quantity" integer,
  PRIMARY KEY ("template_id", "product_id")
);

CREATE TABLE "recurring_order_instance" (
  "id" uuid PRIMARY KEY,
  "template_id" uuid,
  "scheduled_for" date,
  "customer_order_id" uuid,
  "status" text,
  "created_at" timestamptz
);

CREATE TABLE "notification" (
  "id" uuid PRIMARY KEY,
  "user_id" uuid,
  "type" notification_type,
  "channel" notification_channel,
  "title" text,
  "body" text,
  "data" jsonb,
  "is_read" boolean,
  "created_at" timestamptz
);

CREATE TABLE "content_post" (
  "id" uuid PRIMARY KEY,
  "producer_id" uuid,
  "kind" text,
  "title" text,
  "body" text,
  "seasonal_tag" text,
  "created_at" timestamptz
);

CREATE TABLE "content_product_link" (
  "content_id" uuid,
  "product_id" uuid,
  PRIMARY KEY ("content_id", "product_id")
);

CREATE UNIQUE INDEX ON "producer_order" ("customer_order_id", "producer_id");

CREATE UNIQUE INDEX ON "producer_settlement" ("settlement_week_id", "producer_id");

CREATE UNIQUE INDEX ON "product_review" ("product_id", "customer_id");

ALTER TABLE "producer_profile" ADD FOREIGN KEY ("user_id") REFERENCES "app_user" ("id");

ALTER TABLE "producer_profile" ADD FOREIGN KEY ("business_address_id") REFERENCES "address" ("id");

ALTER TABLE "customer_profile" ADD FOREIGN KEY ("user_id") REFERENCES "app_user" ("id");

ALTER TABLE "customer_profile" ADD FOREIGN KEY ("delivery_address_id") REFERENCES "address" ("id");

ALTER TABLE "product" ADD FOREIGN KEY ("producer_id") REFERENCES "producer_profile" ("user_id");

ALTER TABLE "product" ADD FOREIGN KEY ("category_id") REFERENCES "product_category" ("id");

ALTER TABLE "product_allergen" ADD FOREIGN KEY ("product_id") REFERENCES "product" ("id");

ALTER TABLE "product_allergen" ADD FOREIGN KEY ("allergen_id") REFERENCES "allergen" ("id");

ALTER TABLE "product_image" ADD FOREIGN KEY ("product_id") REFERENCES "product" ("id");

ALTER TABLE "surplus_deal" ADD FOREIGN KEY ("product_id") REFERENCES "product" ("id");

ALTER TABLE "cart" ADD FOREIGN KEY ("customer_id") REFERENCES "customer_profile" ("user_id");

ALTER TABLE "cart_item" ADD FOREIGN KEY ("cart_id") REFERENCES "cart" ("id");

ALTER TABLE "cart_item" ADD FOREIGN KEY ("product_id") REFERENCES "product" ("id");

ALTER TABLE "customer_order" ADD FOREIGN KEY ("customer_id") REFERENCES "customer_profile" ("user_id");

ALTER TABLE "customer_order" ADD FOREIGN KEY ("delivery_address_id") REFERENCES "address" ("id");

ALTER TABLE "producer_order" ADD FOREIGN KEY ("customer_order_id") REFERENCES "customer_order" ("id");

ALTER TABLE "producer_order" ADD FOREIGN KEY ("producer_id") REFERENCES "producer_profile" ("user_id");

ALTER TABLE "order_item" ADD FOREIGN KEY ("customer_order_id") REFERENCES "customer_order" ("id");

ALTER TABLE "order_item" ADD FOREIGN KEY ("producer_order_id") REFERENCES "producer_order" ("id");

ALTER TABLE "order_item" ADD FOREIGN KEY ("product_id") REFERENCES "product" ("id");

ALTER TABLE "payment_transaction" ADD FOREIGN KEY ("customer_order_id") REFERENCES "customer_order" ("id");

ALTER TABLE "order_commission" ADD FOREIGN KEY ("customer_order_id") REFERENCES "customer_order" ("id");

ALTER TABLE "order_commission" ADD FOREIGN KEY ("commission_policy_id") REFERENCES "commission_policy" ("id");

ALTER TABLE "producer_settlement" ADD FOREIGN KEY ("settlement_week_id") REFERENCES "settlement_week" ("id");

ALTER TABLE "producer_settlement" ADD FOREIGN KEY ("producer_id") REFERENCES "producer_profile" ("user_id");

ALTER TABLE "producer_order_settlement_link" ADD FOREIGN KEY ("producer_order_id") REFERENCES "producer_order" ("id");

ALTER TABLE "producer_order_settlement_link" ADD FOREIGN KEY ("producer_settlement_id") REFERENCES "producer_settlement" ("id");

ALTER TABLE "product_review" ADD FOREIGN KEY ("product_id") REFERENCES "product" ("id");

ALTER TABLE "product_review" ADD FOREIGN KEY ("customer_id") REFERENCES "customer_profile" ("user_id");

ALTER TABLE "recurring_order_template" ADD FOREIGN KEY ("customer_id") REFERENCES "customer_profile" ("user_id");

ALTER TABLE "recurring_order_item" ADD FOREIGN KEY ("template_id") REFERENCES "recurring_order_template" ("id");

ALTER TABLE "recurring_order_item" ADD FOREIGN KEY ("product_id") REFERENCES "product" ("id");

ALTER TABLE "recurring_order_instance" ADD FOREIGN KEY ("template_id") REFERENCES "recurring_order_template" ("id");

ALTER TABLE "recurring_order_instance" ADD FOREIGN KEY ("customer_order_id") REFERENCES "customer_order" ("id");

ALTER TABLE "notification" ADD FOREIGN KEY ("user_id") REFERENCES "app_user" ("id");

ALTER TABLE "content_post" ADD FOREIGN KEY ("producer_id") REFERENCES "producer_profile" ("user_id");

ALTER TABLE "content_product_link" ADD FOREIGN KEY ("content_id") REFERENCES "content_post" ("id");

ALTER TABLE "content_product_link" ADD FOREIGN KEY ("product_id") REFERENCES "product" ("id");
