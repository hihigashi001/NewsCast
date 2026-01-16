"use client";

import { useEffect, useState } from "react";
import { db } from "@/lib/firebase";
import {
  collection,
  query,
  where,
  orderBy,
  getDocs,
  deleteDoc,
  doc,
  writeBatch,
  serverTimestamp,
} from "firebase/firestore";
import NewsCard from "@/components/NewsCard";

export interface NewsItem {
  id: string;
  category: string;
  title: string;
  link: string;
  summary: string;
  pub_date: string;
  created_at: any;
  status: "unread" | "selected" | "archived";
}

export default function HomePage() {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedNews, setSelectedNews] = useState<Set<string>>(new Set());
  const [filterCategory, setFilterCategory] = useState<string>("すべて");
  const [filterStatus, setFilterStatus] = useState<string>("unread");
  const [updating, setUpdating] = useState(false);

  const categories = [
    "すべて",
    "主要",
    "国内",
    "国際",
    "経済",
    "エンタメ",
    "スポーツ",
    "IT",
  ];

  const statusOptions = [
    { value: "unread", label: "未読", color: "bg-blue-500" },
    { value: "selected", label: "選択済", color: "bg-green-500" },
    { value: "archived", label: "アーカイブ", color: "bg-gray-500" },
  ];

  // ニュースデータの取得
  useEffect(() => {
    const fetchNews = async () => {
      setLoading(true);
      try {
        let q;
        if (filterStatus === "all") {
          q = query(collection(db, "news"), orderBy("created_at", "desc"));
        } else {
          q = query(
            collection(db, "news"),
            where("status", "==", filterStatus),
            orderBy("created_at", "desc")
          );
        }
        const querySnapshot = await getDocs(q);

        const newsData: NewsItem[] = [];
        querySnapshot.forEach((doc) => {
          newsData.push({ id: doc.id, ...doc.data() } as NewsItem);
        });

        setNews(newsData);
        setSelectedNews(new Set()); // フィルタ変更時は選択をリセット
      } catch (error: unknown) {
        console.error("ニュースの取得に失敗しました:", error);

        // Firestore インデックスエラーの場合、リンクを表示
        if (error instanceof Error && error.message.includes("index")) {
          console.error(
            "インデックスが必要です。上記のエラーメッセージ内のリンクをクリックしてインデックスを作成してください。"
          );
        }

        // Firebase 設定エラーの詳細を表示
        if (error instanceof Error) {
          alert(`Firestore エラー: ${error.message}`);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchNews();
  }, [filterStatus]);

  // チェックボックスのトグル（制限なし）
  const toggleSelection = (id: string) => {
    const newSelection = new Set(selectedNews);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    setSelectedNews(newSelection);
  };

  // 表示中の全て選択
  const selectAll = () => {
    const newsToSelect = filteredNews.map((item) => item.id);
    setSelectedNews(new Set(newsToSelect));
  };

  // 全解除
  const clearSelection = () => {
    setSelectedNews(new Set());
  };

  // 選択したニュースを削除
  const deleteSelected = async () => {
    if (!confirm(`選択した${selectedNews.size}件のニュースを削除しますか？`)) {
      return;
    }

    setUpdating(true);
    try {
      const deletePromises = Array.from(selectedNews).map((id) =>
        deleteDoc(doc(db, "news", id))
      );
      await Promise.all(deletePromises);

      // ローカル状態を更新
      setNews(news.filter((item) => !selectedNews.has(item.id)));
      setSelectedNews(new Set());
      alert("削除が完了しました");
    } catch (error) {
      console.error("削除に失敗しました:", error);
      alert("削除に失敗しました");
    } finally {
      setUpdating(false);
    }
  };

  // 選択した記事を「selected」ステータスに更新
  const markAsSelected = async () => {
    if (selectedNews.size === 0) return;

    setUpdating(true);
    try {
      const batch = writeBatch(db);

      selectedNews.forEach((id) => {
        const docRef = doc(db, "news", id);
        batch.update(docRef, {
          status: "selected",
          selected_at: serverTimestamp(),
        });
      });

      await batch.commit();

      // ローカル状態を更新（unread表示中なら削除、それ以外ならステータス更新）
      if (filterStatus === "unread") {
        setNews(news.filter((item) => !selectedNews.has(item.id)));
      } else {
        setNews(
          news.map((item) =>
            selectedNews.has(item.id) ? { ...item, status: "selected" } : item
          )
        );
      }
      setSelectedNews(new Set());
      alert(`${selectedNews.size}件の記事を「選択済」に更新しました`);
    } catch (error) {
      console.error("ステータス更新に失敗しました:", error);
      alert("ステータス更新に失敗しました");
    } finally {
      setUpdating(false);
    }
  };

  // フィルタリング（カテゴリのみ。ステータスはクエリで）
  const filteredNews =
    filterCategory === "すべて"
      ? news
      : news.filter((item) => item.category === filterCategory);

  // カテゴリごとの件数を取得
  const getCategoryCount = (category: string) => {
    if (category === "すべて") return news.length;
    return news.filter((item) => item.category === category).length;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
        <div className="text-xl text-gray-600 dark:text-gray-300">
          読み込み中...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* ヘッダー */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-800 dark:text-white mb-2">
            NewsCast Dashboard
          </h1>
          <p className="text-gray-600 dark:text-gray-300">
            ニュース記事を管理し、動画生成用に選択します
          </p>
        </div>

        {/* ステータスフィルタ */}
        <div className="mb-6">
          <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
            ステータス
          </div>
          <div className="flex flex-wrap gap-2">
            {statusOptions.map((status) => (
              <button
                key={status.value}
                onClick={() => setFilterStatus(status.value)}
                className={`px-4 py-2 rounded-full font-medium transition-colors flex items-center gap-2 ${
                  filterStatus === status.value
                    ? "bg-indigo-600 text-white"
                    : "bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-indigo-100 dark:hover:bg-gray-600"
                }`}
              >
                <span className={`w-2 h-2 rounded-full ${status.color}`}></span>
                {status.label}
              </button>
            ))}
          </div>
        </div>

        {/* カテゴリフィルタ */}
        <div className="mb-6">
          <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
            カテゴリ
          </div>
          <div className="flex flex-wrap gap-2">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setFilterCategory(cat)}
                className={`px-4 py-2 rounded-full font-medium transition-colors ${
                  filterCategory === cat
                    ? "bg-indigo-600 text-white"
                    : "bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-indigo-100 dark:hover:bg-gray-600"
                }`}
              >
                {cat}
                <span className="ml-1 text-xs opacity-70">
                  ({getCategoryCount(cat)})
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* アクションバー */}
        <div className="mb-6 p-4 bg-white dark:bg-gray-800 rounded-xl shadow-sm">
          <div className="flex flex-wrap gap-4 items-center">
            <div className="text-sm text-gray-600 dark:text-gray-300 font-medium">
              {selectedNews.size > 0 ? (
                <span className="text-indigo-600 dark:text-indigo-400">
                  {selectedNews.size}件選択中
                </span>
              ) : (
                <span>{filteredNews.length}件の記事</span>
              )}
            </div>

            <div className="flex-1" />

            {/* 一括選択ボタン */}
            <button
              onClick={selectAll}
              disabled={filteredNews.length === 0 || updating}
              className={`px-4 py-2 rounded-lg font-medium transition-all ${
                filteredNews.length > 0 && !updating
                  ? "bg-blue-600 text-white hover:bg-blue-700"
                  : "bg-gray-300 text-gray-500 cursor-not-allowed"
              }`}
            >
              全選択
            </button>

            <button
              onClick={clearSelection}
              disabled={selectedNews.size === 0 || updating}
              className={`px-4 py-2 rounded-lg font-medium transition-all ${
                selectedNews.size > 0 && !updating
                  ? "bg-gray-600 text-white hover:bg-gray-700"
                  : "bg-gray-300 text-gray-500 cursor-not-allowed"
              }`}
            >
              全解除
            </button>

            {/* 選択確定ボタン（unread の場合のみ表示） */}
            {filterStatus === "unread" && (
              <button
                onClick={markAsSelected}
                disabled={selectedNews.size === 0 || updating}
                className={`px-6 py-2 rounded-lg font-semibold transition-all ${
                  selectedNews.size > 0 && !updating
                    ? "bg-green-600 text-white hover:bg-green-700 shadow-lg"
                    : "bg-gray-300 text-gray-500 cursor-not-allowed"
                }`}
              >
                {updating ? "更新中..." : "選択確定"}
              </button>
            )}

            {/* 削除ボタン */}
            <button
              onClick={deleteSelected}
              disabled={selectedNews.size === 0 || updating}
              className={`px-6 py-2 rounded-lg font-semibold transition-all ${
                selectedNews.size > 0 && !updating
                  ? "bg-red-600 text-white hover:bg-red-700"
                  : "bg-gray-300 text-gray-500 cursor-not-allowed"
              }`}
            >
              削除
            </button>
          </div>
        </div>

        {/* ニュース一覧 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredNews.map((item) => (
            <NewsCard
              key={item.id}
              news={item}
              isSelected={selectedNews.has(item.id)}
              onToggle={() => toggleSelection(item.id)}
            />
          ))}
        </div>

        {filteredNews.length === 0 && (
          <div className="text-center text-gray-500 dark:text-gray-400 py-12">
            <div className="text-4xl mb-4">📭</div>
            <div>
              {filterStatus === "unread"
                ? "未読の記事がありません"
                : filterStatus === "selected"
                ? "選択済みの記事がありません"
                : "アーカイブされた記事がありません"}
            </div>
          </div>
        )}

        {/* ステータス情報 */}
        <div className="mt-8 p-4 bg-white dark:bg-gray-800 rounded-xl shadow-sm">
          <h3 className="font-semibold text-gray-700 dark:text-gray-200 mb-3">
            動画生成について
          </h3>
          <div className="text-sm text-gray-600 dark:text-gray-400 space-y-2">
            <p>
              • 「選択確定」ボタンで記事を「選択済」に変更すると、毎日 JST 2:15
              の自動生成で使用されます
            </p>
            <p>• 動画生成時は「選択済」の記事から3件が自動的に選ばれます</p>
            <p>• 生成完了後、使用された記事は「アーカイブ」に移動します</p>
          </div>
        </div>
      </div>
    </div>
  );
}
