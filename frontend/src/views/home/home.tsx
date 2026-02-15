"use client";

import { IWebServiceResult } from "@/services/BaseService";
import { GetCategoriesService, GetHeroBannersService, GetProductsService, GetReviewsService } from "@/services/services";
import { ICategory, IEachProduct, IHeroBanner, IReview } from "@/types/types";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Links } from "@/constants/links";
import { useLanguage } from "@/providers/LanguageProvider";
import Herosection from "@/components/sections/Herosection";
import TodayShowcase from "@/components/sections/TodayShowcase";
import { baseUrl } from "@/constants/endpoints";

const Home = () => {
  const { lang, dictionary } = useLanguage();
  const [products, setProducts] = useState<IEachProduct[]>([]);
  const [categories, setCategories] = useState<ICategory[]>([]);
  const [reviews, setReviews] = useState<IReview[]>([]);
  const [heroBanners, setHeroBanners] = useState<IHeroBanner[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadedCount, setLoadedCount] = useState(0);

  const ProductsServiceCallback = (resultData: IEachProduct[], result: IWebServiceResult) => {
    if (!result.hasError) {
      setProducts(resultData);
    }
    setLoadedCount((prev) => prev + 1);
  };

  const CategoriesServiceCallback = (resultData: ICategory[], result: IWebServiceResult) => {
    if (!result.hasError) {
      setCategories(resultData);
    }
    setLoadedCount((prev) => prev + 1);
  };

  const ReviewsServiceCallback = (resultData: IReview[], result: IWebServiceResult) => {
    if (!result.hasError) {
      setReviews(resultData.filter((item) => item.is_published).slice(0, 6));
    }
    setLoadedCount((prev) => prev + 1);
  };

  const HeroServiceCallback = (resultData: IHeroBanner[], result: IWebServiceResult) => {
    if (!result.hasError && Array.isArray(resultData)) {
      setHeroBanners(resultData.filter((item) => item.is_active).sort((a, b) => a.sort_order - b.sort_order));
    }
  };

  useEffect(() => {
    GetProductsService(ProductsServiceCallback);
    GetCategoriesService(CategoriesServiceCallback);
    GetReviewsService(ReviewsServiceCallback);
    GetHeroBannersService(HeroServiceCallback);
  }, []);

  useEffect(() => {
    if (loadedCount >= 3) {
      setLoading(false);
    }
  }, [loadedCount]);

  const getProductImage = (product?: IEachProduct) => {
    if (!product) return "http://127.0.0.1:3002/static/legacy-old/image/no_image.jpg";
    const uploaded = product.uploaded_image || "";
    if (uploaded) {
      return uploaded.startsWith("http") ? uploaded : `${baseUrl}${uploaded}`;
    }
    return product.image || "http://127.0.0.1:3002/static/legacy-old/image/no_image.jpg";
  };

  const categoryCards = categories.map((category) => {
    const productsByCategory = products.filter((p) => p.category === category.name);
    const primary = productsByCategory[0];
    const secondary = productsByCategory[1] || productsByCategory[0];
    return {
      id: category.id,
      name: category.name,
      image: getProductImage(primary),
      hoverImage: getProductImage(secondary),
    };
  });

  const renderStars = (rating: number) => {
    const value = Math.max(1, Math.min(5, rating || 5));
    return "★★★★★".slice(0, value) + "☆☆☆☆☆".slice(value, 5);
  };

  return (
    <main>
      <Herosection banners={heroBanners} />
      <TodayShowcase />
      <div className="px-5 md:px-10 lg:px-16 py-8 md:py-12">
      <section className="mb-8 md:mb-10">
        <h1 className="text-3xl md:text-4xl font-semibold text-(--PrimaryDark)">
          {dictionary?.home?.shopByCategory?.title || "Категории каталога"}
        </h1>
        <p className="text-sm md:text-base text-(--PrimaryDark)/70 mt-2">
          Выберите раздел и перейдите в подходящую подборку букетов
        </p>
      </section>

      {loading && (
        <div className="h-28 w-full flex justify-center items-center">
          <img alt="logo" src="/logo.png" width={75} height={21} />
        </div>
      )}

      {!loading && (
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5 md:gap-6">
          {categoryCards.map((category) => (
            <Link
              key={category.id}
              href={`${Links.store(lang)}?category=${encodeURIComponent(category.name)}`}
              className="group rounded-2xl border border-(--Primary)/15 bg-white overflow-hidden shadow-[0_10px_24px_rgba(16,24,40,0.08)] hover:shadow-[0_16px_30px_rgba(16,24,40,0.16)] transition-all duration-300"
            >
              <div className="relative w-full aspect-square bg-(--SoftBg)">
                <img
                  alt={category.name}
                  src={category.image}
                  className="absolute inset-0 h-full w-full object-cover opacity-100 group-hover:opacity-0 transition-opacity duration-300"
                />
                <img
                  alt={`${category.name} hover`}
                  src={category.hoverImage}
                  className="absolute inset-0 h-full w-full object-cover opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                />
              </div>
              <div className="p-4 flex flex-col gap-2">
                <h2 className="text-base md:text-lg font-medium leading-snug text-(--PrimaryDark)">
                  {category.name}
                </h2>
                <span className="text-sm text-(--PrimaryDark)/70">
                  Смотреть товары категории
                </span>
              </div>
            </Link>
          ))}
        </section>
      )}

      {!loading && (
        <div className="mt-8 md:mt-10 flex justify-center">
          <Link
            href={Links.store(lang)}
            className="inline-flex items-center justify-center rounded-full px-6 py-3 bg-(--Primary) text-white hover:bg-(--PrimaryDark) transition-colors"
          >
            {dictionary?.home?.shopByCategory?.button || "Все категории"}
          </Link>
        </div>
      )}

      {!loading && (
        <section className="mt-12 md:mt-16 rounded-2xl border border-(--Primary)/15 bg-white p-5 md:p-8">
          <h2 className="text-2xl md:text-3xl font-semibold text-(--PrimaryDark)">
            Отзывы клиентов
          </h2>
          <p className="text-sm md:text-base text-(--PrimaryDark)/70 mt-2">
            Раздел заполняется из админки Django
          </p>
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-5">
            {reviews.map((review) => (
              <article
                key={review.id}
                className="rounded-xl border border-(--Primary)/10 bg-(--SoftBg) p-4 flex flex-col gap-3"
              >
                <div className="flex items-center gap-3">
                  {review.image ? (
                    <img
                      src={review.image}
                      alt={review.company || review.author}
                      className="w-10 h-10 rounded-full object-cover bg-white"
                    />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-(--Primary)/20" />
                  )}
                  <div>
                    <p className="text-sm font-semibold text-(--PrimaryDark)">
                      {review.company || review.author}
                    </p>
                    <p className="text-xs text-(--PrimaryDark)/70">{review.author}</p>
                  </div>
                </div>
                <p className="text-sm text-(--PrimaryDark)/85 leading-relaxed line-clamp-6">
                  {review.text}
                </p>
                <div className="text-amber-500 text-sm tracking-wide">
                  {renderStars(review.rating)}
                </div>
              </article>
            ))}
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href={Links.reviews(lang)}
              className="inline-flex items-center justify-center rounded-full px-5 py-2 bg-(--Primary) text-white hover:bg-(--PrimaryDark) transition-colors"
            >
              Все отзывы
            </Link>
            <Link
              href={`${Links.reviews(lang)}#review-form`}
              className="inline-flex items-center justify-center rounded-full px-5 py-2 border border-(--Primary) text-(--PrimaryDark) hover:bg-(--SoftBg) transition-colors"
            >
              Оставить отзыв
            </Link>
          </div>
        </section>
      )}
      </div>
    </main>
  );
};

export default Home;
