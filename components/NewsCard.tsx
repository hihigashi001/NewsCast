import { NewsItem } from "@/app/page";

interface NewsCardProps {
  news: NewsItem;
  isSelected: boolean;
  onToggle: () => void;
}

export default function NewsCard({
  news,
  isSelected,
  onToggle,
}: NewsCardProps) {
  const categoryColors: Record<string, string> = {
    主要: "bg-red-500",
    国内: "bg-blue-500",
    国際: "bg-green-500",
    経済: "bg-yellow-500",
    エンタメ: "bg-pink-500",
    スポーツ: "bg-orange-500",
    IT: "bg-purple-500",
  };

  const statusConfig: Record<string, { label: string; color: string }> = {
    unread: { label: "未読", color: "bg-blue-100 text-blue-700" },
    selected: { label: "選択済", color: "bg-green-100 text-green-700" },
    archived: { label: "アーカイブ", color: "bg-gray-100 text-gray-700" },
  };

  const status = statusConfig[news.status] || statusConfig.unread;

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-xl shadow-lg p-5 transition-all hover:shadow-xl cursor-pointer border-2 ${
        isSelected
          ? "border-indigo-600 ring-2 ring-indigo-200"
          : "border-transparent"
      }`}
      onClick={onToggle}
    >
      {/* ヘッダー: カテゴリ + ステータス + チェックボックス */}
      <div className="flex items-center gap-2 mb-3">
        <span
          className={`${
            categoryColors[news.category] || "bg-gray-500"
          } text-white text-xs font-semibold px-3 py-1 rounded-full`}
        >
          {news.category}
        </span>
        <span
          className={`${status.color} text-xs font-medium px-2 py-0.5 rounded`}
        >
          {status.label}
        </span>
        <div className="flex-1" />
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onToggle}
          className="w-5 h-5 cursor-pointer accent-indigo-600"
          onClick={(e) => e.stopPropagation()}
        />
      </div>

      {/* タイトル */}
      <h3 className="text-lg font-bold text-gray-800 dark:text-white mb-2 line-clamp-2">
        {news.title}
      </h3>

      {/* 要約 */}
      {news.summary && (
        <p className="text-sm text-gray-600 dark:text-gray-300 mb-3 line-clamp-3">
          {news.summary}
        </p>
      )}

      {/* フッター: 日時 + リンク */}
      <div className="flex items-center justify-between">
        <div className="text-xs text-gray-500 dark:text-gray-400">
          {news.pub_date || "日時不明"}
        </div>
        <a
          href={news.link}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-indigo-600 hover:text-indigo-800 dark:text-indigo-400"
          onClick={(e) => e.stopPropagation()}
        >
          元記事 →
        </a>
      </div>
    </div>
  );
}
