import { baseUrl, endpoints } from "@/constants/endpoints";
import { ICategory, IEachProduct } from "@/types/types";

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch (error) {
    console.error(`Fetch failed for ${url}`, error);
    return null;
  }
}

export const GetAllProducts = async () => {
  const products = await fetchJson<IEachProduct[]>(`${baseUrl}${endpoints.products}/`);
  return products ?? [];
};

export const GetAllCategories = async () => {
  const categories = await fetchJson<ICategory[]>(`${baseUrl}${endpoints.categories}/`);
  return categories ?? [];
};

export const GetProductByID = async (id: string) => {
  return fetchJson<IEachProduct>(`${baseUrl}${endpoints.products}/${id}/`);
};
