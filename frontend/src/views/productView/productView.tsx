"use client";

import { IEachProduct } from "@/types/types";
import React, { useMemo, useState } from "react";
import Link from "next/link";
import { Links } from "@/constants/links";
import { useLanguage } from "@/providers/LanguageProvider";
import { useShoppingItemsContext } from "@/context/context";

type TRow = {
  index: number;
  name: string;
  qty: string;
};

const decodeHtml = (value: string): string =>
  value
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">");

const stripTags = (value: string): string =>
  decodeHtml(value.replace(/<[^>]*>/g, ""))
    .replace(/\s+/g, " ")
    .trim();

const parseComposition = (description?: string): TRow[] => {
  if (!description) return [];

  const rowRegex = /<tr\b[^>]*>([\s\S]*?)<\/tr>/gi;
  const cellRegex = /<td\b[^>]*>([\s\S]*?)<\/td>/gi;
  const rows: TRow[] = [];
  let rowMatch: RegExpExecArray | null = rowRegex.exec(description);

  while (rowMatch) {
    const rowHtml = rowMatch[1];
    const cells: string[] = [];
    let cellMatch: RegExpExecArray | null = cellRegex.exec(rowHtml);

    while (cellMatch) {
      cells.push(stripTags(cellMatch[1]));
      cellMatch = cellRegex.exec(rowHtml);
    }

    const name = cells[0] || "";
    const qty = cells[1] || "-";
    if (name) rows.push({ index: rows.length + 1, name, qty });

    rowMatch = rowRegex.exec(description);
  }

  return rows;
};

const ProductView = ({ product, resolvedParams }: { product: IEachProduct; resolvedParams: { id: string } }) => {
  const { lang } = useLanguage();
  const { handleIncreaseProduct } = useShoppingItemsContext();
  const [qty, setQty] = useState(1);
  const [selectedImage, setSelectedImage] = useState(product.image);
  const compositionRows = useMemo(() => parseComposition(product.description), [product.description]);
  const productPrice = Number(product.price || 0).toFixed(2);

  const handleAddToCart = () => {
    const count = Number.isFinite(qty) && qty > 0 ? Math.floor(qty) : 1;
    for (let i = 0; i < count; i += 1) handleIncreaseProduct(resolvedParams.id);
  };

  return (
    <div className="lg:px-8 px-4 py-6">
      <div className="bg-white border border-gray-200 rounded-lg p-4 md:p-6">
        <h1 className="text-3xl font-semibold text-(--PrimaryDark) mb-4">{product.title}</h1>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div className="border border-gray-300 p-1 rounded-md w-fit bg-white">
              <img
                src={selectedImage}
                alt={product.title}
                className="w-[280px] h-[280px] md:w-[360px] md:h-[360px] object-cover"
              />
            </div>
            <div className="flex gap-2 mt-3">
              <button
                type="button"
                className="border border-gray-300 rounded p-1 bg-white"
                onClick={() => setSelectedImage(product.image)}
              >
                <img src={product.image} alt={product.title} className="w-16 h-16 object-cover" />
              </button>
            </div>
          </div>

          <div className="pt-1">
            <p className="text-gray-500 text-sm mb-2">{product.article ? `(Артикул: ${product.article})` : ""}</p>
            <p className="text-2xl text-(--PrimaryDark) font-semibold mb-3">Цена: {productPrice} BYN</p>

            <div className="flex items-center gap-2 mb-3">
              <label htmlFor="qty" className="text-sm text-(--PrimaryDark)">
                Количество:
              </label>
              <input
                id="qty"
                type="number"
                min={1}
                value={qty}
                onChange={(e) => setQty(Number(e.target.value) || 1)}
                className="w-16 border border-gray-400 px-2 py-1"
              />
            </div>

            <button
              type="button"
              onClick={handleAddToCart}
              className="bg-(--Primary) hover:bg-(--PrimaryDark) text-white px-4 py-2 rounded"
            >
              В корзину
            </button>
          </div>
        </div>

        <div className="mt-6">
          <h2 className="text-4xl md:text-4xl text-(--PrimaryDark) mb-3">В букет входят</h2>
          {compositionRows.length > 0 ? (
            <div className="border border-gray-200 rounded-md overflow-hidden">
              <table className="w-full text-sm">
                <tbody>
                  {compositionRows.map((row) => (
                    <tr key={`${row.index}-${row.name}`} className="border-b border-gray-100 last:border-b-0">
                      <td className="w-16 px-4 py-2 text-gray-500">{row.index}</td>
                      <td className="px-4 py-2 text-gray-700">{row.name}</td>
                      <td className="w-24 px-4 py-2 text-right font-semibold text-(--PrimaryDark)">{row.qty}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div
              className="text-sm text-gray-700 border border-gray-200 rounded-md p-4"
              dangerouslySetInnerHTML={{ __html: product.description || "Состав временно не указан." }}
            />
          )}
        </div>

        <div className="mt-4">
          <Link href={Links.store(lang)} className="inline-block border border-gray-300 px-4 py-2 rounded">
            Назад
          </Link>
        </div>
      </div>
    </div>
  );
};

export default ProductView;
