"use client"

import ButtonUI from '@/components/ButtonUI';
import { Links } from '@/constants/links';
import { baseUrl } from '@/constants/endpoints';
import { useLanguage } from '@/providers/LanguageProvider';
import { IWebServiceResult } from '@/services/BaseService';
import { PatchProductsService } from '@/services/services';
import { IEachProduct } from '@/types/types';
import Link from 'next/link';
import { useMemo, useState } from 'react';

const DashboardProducts = ({ allProducts }: { allProducts: IEachProduct[] }) => {
    const { lang, dictionary } = useLanguage()
    const [products, setProducts] = useState<IEachProduct[]>(allProducts)
    const [draftPrices, setDraftPrices] = useState<Record<string, string>>({})
    const [savingId, setSavingId] = useState<string | null>(null)
    const [message, setMessage] = useState<string>('')

    const sortedProducts = useMemo(
        () => [...products].sort((a, b) => String(a.title).localeCompare(String(b.title))),
        [products]
    )

    const setDraft = (id: string, value: string) => {
        setDraftPrices((prev) => ({ ...prev, [id]: value }))
    }

    const getDraft = (item: IEachProduct): string => {
        const value = draftPrices[item.id]
        if (value !== undefined) return value
        return String(item.price ?? '')
    }

    const normalizePrice = (raw: string): string | null => {
        const normalized = raw.replace(',', '.').trim()
        if (!normalized) return null
        const numeric = Number(normalized)
        if (!Number.isFinite(numeric) || numeric <= 0) return null
        return numeric.toFixed(2)
    }

    const changedProducts = useMemo(() => {
        return products.filter((item) => {
            const draft = getDraft(item)
            const normalizedDraft = normalizePrice(draft)
            if (!normalizedDraft) return false
            const current = Number(item.price).toFixed(2)
            return normalizedDraft !== current
        })
    }, [products, draftPrices])

    const patchPrice = (item: IEachProduct, price: string): Promise<boolean> => {
        return new Promise((resolve) => {
            PatchProductsService({ price }, String(item.id), (_resultData: unknown, result: IWebServiceResult) => {
                if (result.hasError) {
                    resolve(false)
                    return
                }
                setProducts((prev) =>
                    prev.map((product) =>
                        String(product.id) === String(item.id) ? { ...product, price: Number(price) } : product
                    )
                )
                setDraftPrices((prev) => ({ ...prev, [item.id]: price }))
                resolve(true)
            })
        })
    }

    const savePrice = (item: IEachProduct) => {
        const raw = getDraft(item)
        const price = normalizePrice(raw)
        if (!price) {
            setMessage(`Некорректная цена для "${item.title}"`)
            return
        }

        setSavingId(item.id)
        patchPrice(item, price).then((ok) => {
            setSavingId(null)
            setMessage(ok ? `Цена обновлена: ${item.title}` : `Ошибка сохранения: ${item.title}`)
        })
    }

    const saveAllChanged = async () => {
        if (!changedProducts.length) {
            setMessage('Нет изменений для сохранения')
            return
        }

        setSavingId('all')
        let successCount = 0
        let failedCount = 0

        for (const item of changedProducts) {
            const normalized = normalizePrice(getDraft(item))
            if (!normalized) {
                failedCount += 1
                continue
            }
            const ok = await patchPrice(item, normalized)
            if (ok) successCount += 1
            else failedCount += 1
        }

        setSavingId(null)
        if (failedCount === 0) {
            setMessage(`Сохранено позиций: ${successCount}`)
        } else {
            setMessage(`Сохранено: ${successCount}, ошибок: ${failedCount}`)
        }
    }

    const getImageSrc = (item: IEachProduct): string => {
        const uploaded = item.uploaded_image || ''
        if (uploaded) {
            return uploaded.startsWith('http') ? uploaded : `${baseUrl}${uploaded}`
        }
        return item.image
    }

    return (
        <div className='px-4'>
            <div className='relative'>
                <h2 className="text-center p-5 text-4xl">{dictionary?.dashboard?.product?.productTitle}</h2>
                <div className='absolute right-0 bottom-0 top-0 my-auto flex items-center'>
                    <ButtonUI text={dictionary?.dashboard?.header?.addProduct} url={Links.dashboard.addProduct(lang)} className='bg-(--BabyPink)' />
                </div>
            </div>
            <div className="mb-4 flex items-center justify-end gap-3">
                <button
                    onClick={saveAllChanged}
                    disabled={savingId === 'all'}
                    className="rounded bg-(--Burgundy) px-3 py-1.5 text-sm text-white disabled:opacity-60"
                >
                    {savingId === 'all' ? 'Сохраняю...' : `Сохранить все (${changedProducts.length})`}
                </button>
            </div>
            {message && <div className="mb-3 text-sm text-gray-700">{message}</div>}
            <div className="grid lg:grid-cols-5 md:grid-cols-4 sm:grid-cols-3 grid-cols-2 gap-5 pb-5">
                {sortedProducts.map((eachProduct) => {
                    return (
                        <div
                            key={eachProduct.id}
                            className="border border-(--Primary)/20 rounded-md p-4 flex flex-col gap-3 hover:shadow-md transition-shadow"
                        >
                            <Link href={`${Links.dashboard.product(lang)}/${eachProduct.id}`} className="flex flex-col gap-2 items-center">
                                <div className="sm:w-40 w-full sm:h-40 h-52 flex justify-center bg-(--SoftBg)">
                                    <img alt="" src={getImageSrc(eachProduct)} width={160} height={160} />
                                </div>
                                <div className="w-full flex flex-col items-center text-(--PrimaryDark)">
                                    <span className="text-lg text-center">{eachProduct.title}</span>
                                    <span className="text-sm text-gray-500">Текущая: {Number(eachProduct.price).toFixed(2)} BYN</span>
                                </div>
                            </Link>

                            <div className="flex items-center gap-2">
                                <input
                                    type="text"
                                    value={getDraft(eachProduct)}
                                    onChange={(e) => setDraft(eachProduct.id, e.target.value)}
                                    className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                                    placeholder="Новая цена"
                                />
                                <button
                                    onClick={() => savePrice(eachProduct)}
                                    disabled={savingId === eachProduct.id || savingId === 'all'}
                                    className="rounded bg-emerald-600 px-2 py-1.5 text-xs text-white disabled:opacity-60"
                                >
                                    {savingId === eachProduct.id ? '...' : 'Сохранить'}
                                </button>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    )
}

export default DashboardProducts
