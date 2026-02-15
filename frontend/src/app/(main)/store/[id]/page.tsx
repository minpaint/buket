import { GetProductByID } from "@/services/GetServerSideData";
import { IEachProduct } from "@/types/types";
import ProductView from "@/views/productView/productView";
import { notFound } from "next/navigation";

type TPageProps = {
  params: Promise<{ id: string }>;
  searchParams: Promise<object>;
};

const page = async ({ params }: TPageProps) => {
  const resolvedParams = await params;
  const product: IEachProduct | null = await GetProductByID(resolvedParams.id);
  if (!product) notFound();

  return (<ProductView product={product} resolvedParams={resolvedParams} />);
};

export default page;
