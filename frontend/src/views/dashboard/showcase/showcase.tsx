"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { baseUrl } from "@/constants/endpoints";
import { getAccessToken } from "@/utils/utils";
import { IEachProduct } from "@/types/types";
import { IWebServiceResult } from "@/services/BaseService";
import { GetShowcaseProductsService, PatchProductsService } from "@/services/services";

type CreateForm = {
  title: string;
  price: string;
  description: string;
  showcase_sort_order: string;
};

const defaultCreateForm: CreateForm = {
  title: "",
  price: "",
  description: "",
  showcase_sort_order: "0",
};

const PLACEHOLDER_IMAGE_URL = `${baseUrl}/static/legacy-old/image/no_image.jpg`;

const DashboardShowcase = () => {
  const [showcaseItems, setShowcaseItems] = useState<IEachProduct[]>([]);
  const [createForm, setCreateForm] = useState<CreateForm>(defaultCreateForm);
  const [createImageFile, setCreateImageFile] = useState<File | null>(null);
  const [itemImageFiles, setItemImageFiles] = useState<Record<string, File | null>>({});
  const [status, setStatus] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = () => {
    GetShowcaseProductsService((data: IEachProduct[], result: IWebServiceResult) => {
      if (!result.hasError) setShowcaseItems(data);
    });
  };

  const authHeaders = () => {
    const token = getAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const getImageSrc = (item: IEachProduct) => {
    const uploaded = item.uploaded_image || "";
    if (uploaded) {
      return uploaded.startsWith("http") ? uploaded : `${baseUrl}${uploaded}`;
    }
    return item.image;
  };

  const createShowcaseItem = async () => {
    setStatus("");

    if (!createForm.title || !createForm.price || !createImageFile) {
      setStatus("Заполните название, цену и выберите фото");
      return;
    }

    try {
      const formData = new FormData();
      formData.append("title", createForm.title.trim());
      formData.append("price", String(Number(createForm.price)));
      formData.append("description", createForm.description.trim());
      formData.append("image", PLACEHOLDER_IMAGE_URL);
      formData.append("uploaded_image", createImageFile);
      formData.append("is_online_showcase", "true");
      formData.append("showcase_sort_order", String(Number(createForm.showcase_sort_order || "0")));

      await axios.post(`${baseUrl}/api/products/`, formData, {
        headers: {
          ...authHeaders(),
        },
      });

      setStatus("Позиция добавлена");
      setCreateForm(defaultCreateForm);
      setCreateImageFile(null);
      loadData();
    } catch {
      setStatus("Не удалось добавить позицию");
    }
  };

  const updateShowcaseItem = async (item: IEachProduct) => {
    try {
      const file = itemImageFiles[item.id] || null;
      if (file) {
        const formData = new FormData();
        formData.append("price", String(Number(item.price)));
        formData.append("showcase_sort_order", String(Number(item.showcase_sort_order || 0)));
        formData.append("is_online_showcase", "true");
        formData.append("uploaded_image", file);
        formData.append("image", PLACEHOLDER_IMAGE_URL);

        await axios.patch(`${baseUrl}/api/products/${item.id}/`, formData, {
          headers: {
            ...authHeaders(),
          },
        });
      } else {
        PatchProductsService(
          {
            price: Number(item.price),
            showcase_sort_order: Number(item.showcase_sort_order || 0),
            is_online_showcase: true,
          },
          item.id,
          () => undefined
        );
      }

      setStatus(`Сохранено: "${item.title}"`);
      setItemImageFiles((prev) => ({ ...prev, [item.id]: null }));
      loadData();
    } catch {
      setStatus(`Ошибка сохранения "${item.title}"`);
    }
  };

  const removeFromShowcase = (item: IEachProduct) => {
    PatchProductsService(
      { is_online_showcase: false },
      item.id,
      (_data, result) => {
        if (result.hasError) {
          setStatus(`Не удалось убрать "${item.title}" из витрины`);
          return;
        }
        setStatus(`Убрано из витрины: "${item.title}"`);
        loadData();
      }
    );
  };

  return (
    <div className="px-4 sm:px-6 py-6 flex flex-col gap-6">
      <h2 className="text-3xl sm:text-4xl">ONLINE витрина (Сегодня в наличии)</h2>

      <div className="grid lg:grid-cols-2 gap-3 border rounded-xl p-4 bg-white">
        <input
          className="border rounded-md px-3 py-2"
          placeholder="Название букета *"
          value={createForm.title}
          onChange={(e) => setCreateForm((prev) => ({ ...prev, title: e.target.value }))}
        />
        <input
          className="border rounded-md px-3 py-2"
          placeholder="Цена BYN *"
          value={createForm.price}
          onChange={(e) => setCreateForm((prev) => ({ ...prev, price: e.target.value }))}
        />
        <input
          className="border rounded-md px-3 py-2"
          placeholder="Порядок в списке"
          value={createForm.showcase_sort_order}
          onChange={(e) => setCreateForm((prev) => ({ ...prev, showcase_sort_order: e.target.value }))}
        />
        <div className="border rounded-md px-3 py-2 flex items-center justify-between gap-3">
          <span className="text-sm text-neutral-700 truncate">
            {createImageFile ? createImageFile.name : "Фото не выбрано"}
          </span>
          <label className="rounded-md border px-3 py-1 text-sm cursor-pointer hover:bg-neutral-50">
            Обзор
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => setCreateImageFile(e.target.files?.[0] || null)}
            />
          </label>
        </div>
        <input
          className="border rounded-md px-3 py-2 lg:col-span-2"
          placeholder="Описание"
          value={createForm.description}
          onChange={(e) => setCreateForm((prev) => ({ ...prev, description: e.target.value }))}
        />

        <button
          type="button"
          className="rounded-md bg-(--Primary) text-white px-5 py-2 w-fit"
          onClick={createShowcaseItem}
        >
          Добавить в витрину
        </button>
      </div>

      {status && <p className="text-sm">{status}</p>}

      <div className="grid gap-3">
        {showcaseItems.map((item) => (
          <div key={item.id} className="border rounded-xl p-4 grid lg:grid-cols-12 gap-2 items-center bg-white">
            <img src={getImageSrc(item)} alt={item.title} className="w-full lg:col-span-2 h-28 object-cover rounded-md border" />
            <div className="lg:col-span-3">
              <p className="font-semibold">{item.title}</p>
              <p className="text-xs opacity-70">id: {item.id}</p>
            </div>
            <input
              className="border rounded-md px-2 py-1 lg:col-span-2"
              value={item.price}
              onChange={(e) =>
                setShowcaseItems((prev) =>
                  prev.map((row) => (row.id === item.id ? { ...row, price: Number(e.target.value) } : row))
                )
              }
            />
            <input
              className="border rounded-md px-2 py-1 lg:col-span-1"
              value={item.showcase_sort_order || 0}
              onChange={(e) =>
                setShowcaseItems((prev) =>
                  prev.map((row) =>
                    row.id === item.id ? { ...row, showcase_sort_order: Number(e.target.value) } : row
                  )
                )
              }
            />
            <div className="border rounded-md px-2 py-1 lg:col-span-2 flex items-center justify-between gap-2">
              <span className="text-xs text-neutral-700 truncate">
                {itemImageFiles[item.id] ? itemImageFiles[item.id]!.name : "Фото не выбрано"}
              </span>
              <label className="rounded-md border px-2 py-1 text-xs cursor-pointer hover:bg-neutral-50">
                Обзор
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) =>
                    setItemImageFiles((prev) => ({ ...prev, [item.id]: e.target.files?.[0] || null }))
                  }
                />
              </label>
            </div>
            <div className="lg:col-span-2 flex gap-2">
              <button
                type="button"
                className="rounded-md bg-emerald-600 text-white px-3 py-1 text-sm"
                onClick={() => updateShowcaseItem(item)}
              >
                Сохранить
              </button>
              <button
                type="button"
                className="rounded-md border border-red-500 text-red-600 px-3 py-1 text-sm"
                onClick={() => removeFromShowcase(item)}
              >
                Убрать
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DashboardShowcase;
