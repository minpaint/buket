"use client"

import { useEffect, useMemo, useState } from "react";
import ButtonUI from "@/components/ButtonUI";
import { Links } from "@/constants/links";
import { useLanguage } from "@/providers/LanguageProvider";
import { IHeroBanner } from "@/types/types";

const Herosection = ({ banners }: { banners?: IHeroBanner[] }) => {
  const { lang, dictionary } = useLanguage();
  const [activeIndex, setActiveIndex] = useState(0);

  const slides = useMemo(() => {
    if (banners && banners.length > 0) {
      return banners;
    }
    return [
      {
        id: 0,
        name: "default",
        title: dictionary?.home?.hero?.title || "",
        caption: dictionary?.home?.hero?.caption || "",
        button_text: dictionary?.home?.hero?.button || "",
        button_url: Links.store(lang),
        desktop_image: "/HeroBg.svg",
        mobile_image: "/VerticalHeroBg.svg",
        is_active: true,
        starts_on: null,
        ends_on: null,
        sort_order: 0,
        created_at: "",
        updated_at: "",
      },
    ];
  }, [banners, dictionary, lang]);

  useEffect(() => {
    setActiveIndex((current) => (current >= slides.length ? 0 : current));
  }, [slides.length]);

  useEffect(() => {
    if (slides.length <= 1) return;
    const timer = setInterval(() => {
      setActiveIndex((current) => (current + 1) % slides.length);
    }, 5000);
    return () => clearInterval(timer);
  }, [slides.length]);

  const activeSlide = slides[activeIndex];
  const desktopBg = activeSlide.desktop_image || "/HeroBg.svg";
  const mobileBg = activeSlide.mobile_image || activeSlide.desktop_image || "/VerticalHeroBg.svg";
  const title = activeSlide.title || dictionary?.home?.hero?.title;
  const caption = activeSlide.caption || dictionary?.home?.hero?.caption;
  const buttonText = activeSlide.button_text || dictionary?.home?.hero?.button;
  const buttonUrl = activeSlide.button_url || Links.store(lang);

  return (
    <div className="shadow relative">
      <div className="absolute inset-0 md:block hidden bg-cover bg-center transition-all duration-700" style={{ backgroundImage: `url('${desktopBg}')` }} />
      <div className="absolute inset-0 md:hidden block bg-cover bg-center transition-all duration-700" style={{ backgroundImage: `url('${mobileBg}')` }} />
      <div className="relative w-full h-[46vh] md:h-[58vh] min-h-[340px] md:min-h-[420px] flex flex-col gap-2 justify-center items-center text-(--Burgundy) px-5 bg-black/20">
        <div className="max-w-4xl rounded-[28px] border border-white/70 bg-gradient-to-b from-white/72 to-white/52 backdrop-blur-xl shadow-[0_14px_36px_rgba(32,18,18,0.18)] px-4 py-4 md:px-9 md:py-7">
          <div className="mx-auto mb-3 h-px w-16 bg-gradient-to-r from-transparent via-(--Burgundy)/55 to-transparent" />
          <h1 className="md:text-5xl text-3xl text-center font-bold sm:px-6 px-2 tracking-tight drop-shadow-[0_1px_0_rgba(255,255,255,0.55)]">
            {title}
          </h1>
          <span className="mt-2 block text-[15px] md:text-lg font-light font-serif text-center max-w-3xl mx-auto text-(--Burgundy)/90">
            {caption?.toUpperCase()}
          </span>
          <div className="h-px w-20 bg-(--Burgundy)/70 mt-4 mb-1 mx-auto"></div>
        </div>
        <ButtonUI
          text={buttonText}
          className="bg-(--Magenta) text-white mt-4 md:w-fit w-full"
          url={buttonUrl}
        />
        {slides.length > 1 && (
          <>
            <button
              type="button"
              aria-label="Предыдущий баннер"
              className="absolute left-3 md:left-6 top-1/2 -translate-y-1/2 h-10 w-10 rounded-full bg-white/70 hover:bg-white text-(--PrimaryDark)"
              onClick={() => setActiveIndex((current) => (current - 1 + slides.length) % slides.length)}
            >
              {"<"}
            </button>
            <button
              type="button"
              aria-label="Следующий баннер"
              className="absolute right-3 md:right-6 top-1/2 -translate-y-1/2 h-10 w-10 rounded-full bg-white/70 hover:bg-white text-(--PrimaryDark)"
              onClick={() => setActiveIndex((current) => (current + 1) % slides.length)}
            >
              {">"}
            </button>
            <div className="absolute bottom-4 flex items-center gap-2">
              {slides.map((slide, index) => (
                <button
                  key={slide.id || index}
                  type="button"
                  aria-label={`Перейти к баннеру ${index + 1}`}
                  className={`h-2.5 rounded-full transition-all ${index === activeIndex ? "w-8 bg-white" : "w-2.5 bg-white/60"}`}
                  onClick={() => setActiveIndex(index)}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default Herosection;
