"use client";

import { useMemo, useState, useEffect } from "react";
import { IWebServiceResult } from "@/services/BaseService";
import { GetReviewsService, PostReviewService } from "@/services/services";
import { IReview, IReviewFormData } from "@/types/types";
import Link from "next/link";
import { Links } from "@/constants/links";
import { useLanguage } from "@/providers/LanguageProvider";

const Reviews = () => {
  const { lang } = useLanguage();
  const [reviews, setReviews] = useState<IReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [minRating, setMinRating] = useState(0);
  const [submitState, setSubmitState] = useState<"idle" | "sending" | "ok" | "error">("idle");
  const [formData, setFormData] = useState<IReviewFormData>({
    author: "",
    company: "",
    text: "",
    rating: 5,
  });

  useEffect(() => {
    GetReviewsService((resultData, result) => {
      setLoading(false);
      if (!result.hasError) {
        setReviews(resultData);
      }
    });
  }, []);

  const filteredReviews = useMemo(() => {
    const q = query.trim().toLowerCase();
    return reviews.filter((item) => {
      if (minRating > 0 && item.rating < minRating) return false;
      if (!q) return true;
      const hay = `${item.author} ${item.company} ${item.text}`.toLowerCase();
      return hay.includes(q);
    });
  }, [reviews, query, minRating]);

  const stars = (rating: number) => {
    const value = Math.max(1, Math.min(5, rating || 5));
    return "★★★★★".slice(0, value) + "☆☆☆☆☆".slice(value, 5);
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSubmitState("sending");
    PostReviewService(formData, (_data: IReview, result: IWebServiceResult<IReview>) => {
      if (!result.hasError) {
        setSubmitState("ok");
        setFormData({ author: "", company: "", text: "", rating: 5 });
        return;
      }
      setSubmitState("error");
    });
  };

  return (
    <main className="px-5 md:px-10 lg:px-16 py-8 md:py-12">
      <section className="mb-6">
        <h1 className="text-3xl md:text-4xl font-semibold text-(--PrimaryDark)">Отзывы клиентов</h1>
        <p className="text-sm md:text-base text-(--PrimaryDark)/70 mt-2">
          Реальные отзывы о работе Buket.by
        </p>
      </section>

      <section className="rounded-2xl border border-(--Primary)/15 bg-white p-4 md:p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Поиск по отзывам"
            className="border border-(--Primary)/25 rounded-lg px-3 py-2"
          />
          <select
            value={minRating}
            onChange={(e) => setMinRating(Number(e.target.value))}
            className="border border-(--Primary)/25 rounded-lg px-3 py-2"
          >
            <option value={0}>Все оценки</option>
            <option value={5}>Только 5 звезд</option>
            <option value={4}>От 4 звезд</option>
            <option value={3}>От 3 звезд</option>
          </select>
          <Link
            href={`${Links.reviews(lang)}#review-form`}
            className="inline-flex items-center justify-center rounded-lg bg-(--Primary) text-white px-4 py-2 hover:bg-(--PrimaryDark) transition-colors"
          >
            Оставить отзыв
          </Link>
        </div>
      </section>

      {loading && (
        <div className="h-24 flex items-center justify-center">
          <img alt="logo" src="/logo.png" width={75} height={21} />
        </div>
      )}

      {!loading && (
        <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-5">
          {filteredReviews.map((review) => (
            <article key={review.id} className="rounded-xl border border-(--Primary)/10 bg-(--SoftBg) p-4 flex flex-col gap-3">
              <div className="flex items-center gap-3">
                {review.image ? (
                  <img src={review.image} alt={review.company || review.author} className="w-10 h-10 rounded-full object-cover bg-white" />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-(--Primary)/20" />
                )}
                <div>
                  <p className="text-sm font-semibold text-(--PrimaryDark)">{review.company || review.author}</p>
                  <p className="text-xs text-(--PrimaryDark)/70">{review.author}</p>
                </div>
              </div>
              <p className="text-sm text-(--PrimaryDark)/85 leading-relaxed">{review.text}</p>
              <div className="text-amber-500 text-sm tracking-wide">{stars(review.rating)}</div>
            </article>
          ))}
        </section>
      )}

      <section id="review-form" className="mt-10 md:mt-12 rounded-2xl border border-(--Primary)/15 bg-white p-5 md:p-7">
        <h2 className="text-2xl md:text-3xl font-semibold text-(--PrimaryDark)">Оставить отзыв</h2>
        <p className="text-sm text-(--PrimaryDark)/70 mt-2">
          Отзыв появится на сайте после проверки администратором.
        </p>
        <form onSubmit={handleSubmit} className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-3">
          <input
            required
            value={formData.author}
            onChange={(e) => setFormData((p) => ({ ...p, author: e.target.value }))}
            placeholder="Ваше имя"
            className="border border-(--Primary)/25 rounded-lg px-3 py-2"
          />
          <input
            value={formData.company || ""}
            onChange={(e) => setFormData((p) => ({ ...p, company: e.target.value }))}
            placeholder="Компания (необязательно)"
            className="border border-(--Primary)/25 rounded-lg px-3 py-2"
          />
          <select
            value={formData.rating}
            onChange={(e) => setFormData((p) => ({ ...p, rating: Number(e.target.value) }))}
            className="border border-(--Primary)/25 rounded-lg px-3 py-2 md:col-span-2"
          >
            <option value={5}>5 — Отлично</option>
            <option value={4}>4 — Хорошо</option>
            <option value={3}>3 — Нормально</option>
            <option value={2}>2 — Плохо</option>
            <option value={1}>1 — Очень плохо</option>
          </select>
          <textarea
            required
            value={formData.text}
            onChange={(e) => setFormData((p) => ({ ...p, text: e.target.value }))}
            placeholder="Текст отзыва"
            rows={5}
            className="border border-(--Primary)/25 rounded-lg px-3 py-2 md:col-span-2"
          />
          <button
            type="submit"
            disabled={submitState === "sending"}
            className="md:col-span-2 inline-flex items-center justify-center rounded-lg bg-(--Primary) text-white px-4 py-2 hover:bg-(--PrimaryDark) transition-colors disabled:opacity-60"
          >
            {submitState === "sending" ? "Отправка..." : "Отправить отзыв"}
          </button>
          {submitState === "ok" && (
            <p className="md:col-span-2 text-green-700 text-sm">
              Спасибо. Отзыв отправлен на модерацию.
            </p>
          )}
          {submitState === "error" && (
            <p className="md:col-span-2 text-red-700 text-sm">
              Не удалось отправить отзыв. Попробуйте еще раз.
            </p>
          )}
        </form>
      </section>
    </main>
  );
};

export default Reviews;

