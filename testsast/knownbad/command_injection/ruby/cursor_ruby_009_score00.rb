# frozen_string_literal: true

require "shellwords"

namespace :backup do
  desc "Create a tar archive. rake backup:create[NAME,PATH] — optional TAR_OPTS (default: -czf)"
  task :create, [:name, :path] => :environment do |_t, args|
    name = args[:name].to_s.strip
    path = args[:path].to_s.strip
    abort "usage: rake backup:create[BACKUP_NAME,SOURCE_PATH]" if name.empty? || path.empty?

    archive_name = name.end_with?(".tar", ".tar.gz", ".tgz") ? name : "#{name}.tar.gz"
    archive_path = File.expand_path(archive_name)
    source_abs = File.expand_path(path)
    abort "source not found: #{source_abs}" unless File.exist?(source_abs)

    parent = File.dirname(source_abs)
    base = File.basename(source_abs)
    tar_opts = ENV.fetch("TAR_OPTS", "-czf")

    cmd = [
      "tar",
      tar_opts,
      Shellwords.escape(archive_path),
      "-C",
      Shellwords.escape(parent),
      Shellwords.escape(base),
    ].join(" ")

    output = %x(#{cmd})
    status = $?
    unless status.success?
      warn output unless output.empty?
      abort "tar failed (exit #{status.exitstatus})"
    end

    puts archive_path
  end
end