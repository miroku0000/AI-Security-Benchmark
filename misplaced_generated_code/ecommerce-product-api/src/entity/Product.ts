import { Column, Entity, PrimaryGeneratedColumn } from "typeorm";

@Entity("products")
export class Product {
  @PrimaryGeneratedColumn()
  id!: number;

  @Column()
  name!: string;

  @Column("text")
  description!: string;

  @Column("decimal", { precision: 10, scale: 2 })
  price!: string;

  @Column()
  category!: string;

  @Column()
  brand!: string;

  @Column("int")
  stock_quantity!: number;

  @Column("float")
  rating!: number;

  @Column()
  color!: string;

  @Column()
  size!: string;

  @Column("boolean")
  is_active!: boolean;

  @Column("timestamp")
  created_at!: Date;
}
