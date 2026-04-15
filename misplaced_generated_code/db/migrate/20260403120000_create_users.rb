class CreateUsers < ActiveRecord::Migration[7.0]
  def change
    create_table :users do |t|
      t.string :email
      t.string :name
      t.text :bio
      t.string :phone
      t.string :location
      t.string :avatar_url
      t.string :website
      t.json :metadata

      t.timestamps
    end

    add_index :users, :email, unique: true
  end
end
