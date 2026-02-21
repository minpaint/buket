import { IProductCardType } from "@/types/types";
import Link from "next/link";
import CardPrice from "./CardPrice";

const ProductCard = ({
  id,
  title,
  price,
  image,
  linkToUrl,
}: IProductCardType) => {
  return (
    <Link
      href={`${linkToUrl}/${id}`}
      className="border border-(--Primary)/20 rounded-md p-4 flex flex-col gap-2 items-center hover:shadow-md transition-shadow"
    >
      <div className="sm:w-40 w-full sm:h-40 h-52 flex justify-center bg-(--SoftBg)">
        <img alt="" src={image} width={160} height={160} />
      </div>
      <div className="w-full flex flex-col items-center text-(--PrimaryDark)">
        <span className="text-lg">{title}</span>
        <CardPrice price={price} justify="items-center" />
      </div>
    </Link>
  );
};

export default ProductCard;
