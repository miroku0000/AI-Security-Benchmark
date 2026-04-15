class CreateEmailLogs < ActiveRecord::Migration[7.0]
  def change
    create_table :email_logs do |t|
      t.string :email, null: false
      t.string :event, null: false
      t.datetime :timestamp, null: false
      t.string :message_id
      t.string :reason
      t.string :url
      t.string :user_agent
      t.string :ip
      t.json :metadata
      
      t.timestamps
    end
    
    add_index :email_logs, :email
    add_index :email_logs, :event
    add_index :email_logs, :timestamp
    add_index :email_logs, :message_id
    add_index :email_logs, [:email, :event]
  end
end