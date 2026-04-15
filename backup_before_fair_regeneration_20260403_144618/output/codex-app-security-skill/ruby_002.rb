class Admin::ReportsController < ApplicationController
  class UnsafeQueryError < StandardError; end