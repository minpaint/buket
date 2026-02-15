"use client";

import { useEffect, useMemo, useState } from "react";
import { IWebServiceResult } from "@/services/BaseService";
import { GetHeroBannersService, PatchHeroBannerService, PostHeroBannerService } from "@/services/services";
import { IHeroBanner } from "@/types/types";

type HeroFormData = {
  name: string;
  title: string;
  caption: string;
  button_text: string;
  button_url: string;
  desktop_image: string;
  mobile_image: string;
  is_active: boolean;
  starts_on: string;
  ends_on: string;
  sort_order: number;
};

const initialForm: HeroFormData = {
  name: "",
  title: "",
  caption: "",
  button_text: "Перейти в каталог",
  button_url: "/store",
  desktop_image: "",
  mobile_image: "",
  is_active: true,
  starts_on: "",
  ends_on: "",
  sort_order: 0,
};

const DashboardHero = () => {
  const [banners, setBanners] = useState<IHeroBanner[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [form, setForm] = useState<HeroFormData>(initialForm);
  const [status, setStatus] = useState<string>("");

  useEffect(() => {
    loadBanners();
  }, []);

  const selectedBanner = useMemo(
    () => banners.find((item) => item.id === selectedId) || null,
    [banners, selectedId]
  );

  useEffect(() => {
    if (!selectedBanner) return;
    setForm({
      name: selectedBanner.name || "",
      title: selectedBanner.title || "",
      caption: selectedBanner.caption || "",
      button_text: selectedBanner.button_text || "",
      button_url: selectedBanner.button_url || "/store",
      desktop_image: selectedBanner.desktop_image || "",
      mobile_image: selectedBanner.mobile_image || "",
      is_active: selectedBanner.is_active,
      starts_on: selectedBanner.starts_on || "",
      ends_on: selectedBanner.ends_on || "",
      sort_order: selectedBanner.sort_order || 0,
    });
  }, [selectedBanner]);

  const loadBanners = () => {
    GetHeroBannersService((resultData: IHeroBanner[], result: IWebServiceResult) => {
      if (result.hasError) {
        setStatus("Не удалось загрузить hero-баннеры");
        return;
      }

      setBanners(resultData);
      if (resultData.length > 0) {
        setSelectedId(resultData[0].id);
      } else {
        setSelectedId(null);
        setForm(initialForm);
      }
    });
  };

  const handleSave = () => {
    setStatus("");

    const payload = {
      name: form.name.trim(),
      title: form.title.trim(),
      caption: form.caption.trim(),
      button_text: form.button_text.trim(),
      button_url: form.button_url.trim(),
      desktop_image: form.desktop_image.trim(),
      mobile_image: form.mobile_image.trim(),
      is_active: form.is_active,
      starts_on: form.starts_on || null,
      ends_on: form.ends_on || null,
      sort_order: Number.isFinite(form.sort_order) ? form.sort_order : 0,
    };

    if (!payload.name || !payload.title || !payload.desktop_image) {
      setStatus("Заполните обязательные поля: название, заголовок и desktop изображение");
      return;
    }

    if (selectedId) {
      PatchHeroBannerService(selectedId, payload, (_data, result) => {
        if (result.hasError) {
          setStatus("Не удалось сохранить изменения");
          return;
        }
        setStatus("Сохранено");
        loadBanners();
      });
      return;
    }

    PostHeroBannerService(payload, (resultData, result) => {
      if (result.hasError) {
        setStatus("Не удалось создать баннер");
        return;
      }
      setStatus("Баннер создан");
      loadBanners();
      setSelectedId(resultData.id);
    });
  };

  return (
    <div className="px-4 sm:px-6 py-6 flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-3xl sm:text-4xl">Hero баннеры</h2>
        <button
          className="rounded-md border px-4 py-2 hover:bg-(--SoftBg)"
          onClick={() => {
            setSelectedId(null);
            setForm(initialForm);
            setStatus("Создание нового баннера");
          }}
          type="button"
        >
          Новый баннер
        </button>
      </div>

      {banners.length > 0 && (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
          {banners.map((banner) => (
            <button
              key={banner.id}
              type="button"
              onClick={() => setSelectedId(banner.id)}
              className={`text-left border rounded-lg p-3 ${
                selectedId === banner.id ? "border-(--Primary) bg-(--SoftBg)" : "border-gray-200"
              }`}
            >
              <p className="font-semibold">{banner.name}</p>
              <p className="text-sm opacity-80">{banner.title}</p>
              <p className="text-xs opacity-70">
                {banner.starts_on || "без даты"} - {banner.ends_on || "без даты"}
              </p>
            </button>
          ))}
        </div>
      )}

      <div className="grid lg:grid-cols-2 gap-4">
        <label className="flex flex-col gap-1">
          <span>Название кампании *</span>
          <input
            className="border rounded-md px-3 py-2"
            value={form.name}
            onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span>Заголовок *</span>
          <input
            className="border rounded-md px-3 py-2"
            value={form.title}
            onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
          />
        </label>
        <label className="flex flex-col gap-1 lg:col-span-2">
          <span>Подзаголовок</span>
          <input
            className="border rounded-md px-3 py-2"
            value={form.caption}
            onChange={(e) => setForm((prev) => ({ ...prev, caption: e.target.value }))}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span>Текст кнопки</span>
          <input
            className="border rounded-md px-3 py-2"
            value={form.button_text}
            onChange={(e) => setForm((prev) => ({ ...prev, button_text: e.target.value }))}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span>Ссылка кнопки</span>
          <input
            className="border rounded-md px-3 py-2"
            value={form.button_url}
            onChange={(e) => setForm((prev) => ({ ...prev, button_url: e.target.value }))}
          />
        </label>
        <label className="flex flex-col gap-1 lg:col-span-2">
          <span>Изображение desktop (URL) *</span>
          <input
            className="border rounded-md px-3 py-2"
            value={form.desktop_image}
            onChange={(e) => setForm((prev) => ({ ...prev, desktop_image: e.target.value }))}
          />
        </label>
        <label className="flex flex-col gap-1 lg:col-span-2">
          <span>Изображение mobile (URL)</span>
          <input
            className="border rounded-md px-3 py-2"
            value={form.mobile_image}
            onChange={(e) => setForm((prev) => ({ ...prev, mobile_image: e.target.value }))}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span>Дата начала</span>
          <input
            type="date"
            className="border rounded-md px-3 py-2"
            value={form.starts_on}
            onChange={(e) => setForm((prev) => ({ ...prev, starts_on: e.target.value }))}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span>Дата окончания</span>
          <input
            type="date"
            className="border rounded-md px-3 py-2"
            value={form.ends_on}
            onChange={(e) => setForm((prev) => ({ ...prev, ends_on: e.target.value }))}
          />
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => setForm((prev) => ({ ...prev, is_active: e.target.checked }))}
          />
          <span>Активен</span>
        </label>
        <label className="flex flex-col gap-1">
          <span>Приоритет</span>
          <input
            type="number"
            className="border rounded-md px-3 py-2"
            value={form.sort_order}
            onChange={(e) => setForm((prev) => ({ ...prev, sort_order: Number(e.target.value) }))}
          />
        </label>
      </div>

      <div className="flex items-center gap-4">
        <button className="rounded-md bg-(--Primary) text-white px-5 py-2" type="button" onClick={handleSave}>
          Сохранить
        </button>
        {status && <span className="text-sm">{status}</span>}
      </div>
    </div>
  );
};

export default DashboardHero;
