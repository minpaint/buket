"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AddToCard from "@/components/AddToCard";
import CardPrice from "@/components/CardPrice";
import { IEachProduct } from "@/types/types";
import { IWebServiceResult } from "@/services/BaseService";
import { GetShowcaseProductsService } from "@/services/services";
import { Links } from "@/constants/links";
import { useLanguage } from "@/providers/LanguageProvider";
import { baseUrl } from "@/constants/endpoints";

const TodayShowcase = () => {
  const { lang } = useLanguage();
  const [products, setProducts] = useState<IEachProduct[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    GetShowcaseProductsService((resultData: IEachProduct[], result: IWebServiceResult) => {
      setLoading(false);
      if (!result.hasError) setProducts(resultData);
    });
  }, []);

  const getImageSrc = (item: IEachProduct) => {
    const uploaded = item.uploaded_image || "";
    if (uploaded) {
      return uploaded.startsWith("http") ? uploaded : `${baseUrl}${uploaded}`;
    }
    return item.image;
  };

  const getHoverImageSrc = (item: IEachProduct) => {
    const primary = getImageSrc(item);
    const fallback = item.image || "";
    if (!fallback) return primary;
    const resolvedFallback = fallback.startsWith("http") ? fallback : `${baseUrl}${fallback}`;
    return resolvedFallback !== primary ? resolvedFallback : primary;
  };

  return (
    <section id="today-showcase" className="px-5 md:px-10 lg:px-16 py-8 md:py-10">
      <div className="rounded-2xl border border-(--Primary)/20 bg-white p-5 md:p-7">
        <h2 className="text-2xl md:text-3xl font-semibold text-(--PrimaryDark)">
          Сегодня в наличии✔️
        </h2>
        <p className="mt-3 text-black">
          ONLINE витрина - собранные сегодня букеты прямо из холодильника.
        </p>
        <p className="mt-2 text-black">
          Выберите понравившийся букет из витрины
          и оформляйте заказ через корзину, либо свяжитесь с нашим менеджером через онлайн чат.
        </p>

        {loading && (
          <div className="h-24 flex items-center justify-center">
            <img alt="logo" src="/logo.png" width={75} height={21} />
          </div>
        )}

        {!loading && (
          <div className="mt-5 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {products.map((item) => (
              <article key={item.id} className="border rounded-xl p-3 flex flex-col gap-3 bg-white shadow-[0_10px_24px_rgba(16,24,40,0.08)] hover:shadow-[0_16px_30px_rgba(16,24,40,0.16)] transition-all duration-300">
                <Link href={`${Links.store(lang)}/${item.id}`} className="block">
                  <div className="group relative w-full aspect-square rounded-md overflow-hidden bg-(--SoftBg)">
                    <img
                      src={getImageSrc(item)}
                      alt={item.title}
                      className="absolute inset-0 w-full h-full object-cover opacity-100 group-hover:opacity-0 transition-opacity duration-300"
                    />
                    <img
                      src={getHoverImageSrc(item)}
                      alt={`${item.title} hover`}
                      className="absolute inset-0 w-full h-full object-cover opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                    />
                  </div>
                </Link>
                <Link href={`${Links.store(lang)}/${item.id}`} className="font-medium text-(--PrimaryDark)">
                  {item.title}
                </Link>
                <CardPrice price={item.price} />
                <AddToCard id={item.id} />
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
};

export default TodayShowcase;
