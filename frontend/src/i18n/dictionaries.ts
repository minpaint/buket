const dictionaries = {
    en: () => import('./en.json').then((module) => module.default),
}

export const getDictionary = (locale?: string) => {
    const validLocale = (locale === 'en') ? locale : 'en'
    return dictionaries[validLocale]()
}
