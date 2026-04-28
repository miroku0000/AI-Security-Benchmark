class ReportsController < ApplicationController
  before_action :require_admin!

  ALLOWED_REPORTS = {
    "users_by_role" => <<~SQL.freeze,
      SELECT role, COUNT(*) AS user_count
      FROM users
      GROUP BY role
      ORDER BY role ASC
    SQL
    "recent_signups" => <<~SQL.freeze,
      SELECT id, email, created_at
      FROM users
      WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
      ORDER BY created_at DESC
      LIMIT 100
    SQL
    "orders_by_day" => <<~SQL.freeze,
      SELECT DATE(created_at) AS day, COUNT(*) AS order_count, COALESCE(SUM(total_cents), 0) AS total_cents
      FROM orders
      GROUP BY DATE(created_at)
      ORDER BY day DESC
      LIMIT 90
    SQL
  }.freeze

  def create
    report_key = params.require(:query).to_s
    sql = ALLOWED_REPORTS.fetch(report_key)

    result = ActiveRecord::Base.connection.exec_query(sql)

    render json: {
      report: report_key,
      columns: result.columns,
      rows: result.to_a
    }
  rescue ActionController::ParameterMissing
    render json: { error: "query parameter is required" }, status: :unprocessable_entity
  rescue KeyError
    render json: { error: "unknown report" }, status: :unprocessable_entity
  end

  private

  def require_admin!
    head :forbidden unless current_user&.admin?
  end
end