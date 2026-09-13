"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { createProduct, listProducts, updateProduct } from "@/lib/api/client";
import type { Product } from "@/lib/api/types";

type ProductForm = {
  product_id: string;
  category: string;
  name: string;
  aliases: string;
  variants: string;
  hs_codes: string;
  priority: string;
};

const emptyForm: ProductForm = {
  product_id: "",
  category: "Spices",
  name: "",
  aliases: "",
  variants: "",
  hs_codes: "",
  priority: "100",
};

function splitList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function joinList(value: string[]) {
  return value.length ? value.join(", ") : "-";
}

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<ProductForm>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setProducts(await listProducts());
      setError(null);
    } catch (error) {
      setError(error instanceof Error ? error.message : "API unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const sortedProducts = useMemo(
    () => [...products].sort((a, b) => a.priority - b.priority || a.name.localeCompare(b.name)),
    [products],
  );

  function edit(product: Product) {
    setEditingId(product.product_id);
    setForm({
      product_id: product.product_id,
      category: product.category,
      name: product.name,
      aliases: product.aliases.join(", "),
      variants: product.variants.join(", "),
      hs_codes: product.hs_codes.join(", "),
      priority: String(product.priority),
    });
  }

  function resetForm() {
    setEditingId(null);
    setForm(emptyForm);
  }

  async function submit() {
    setSaving(true);
    try {
      const payload = {
        category: form.category,
        name: form.name,
        aliases: splitList(form.aliases),
        variants: splitList(form.variants),
        hs_codes: splitList(form.hs_codes),
        priority: Number(form.priority || 100),
      };
      if (editingId) {
        await updateProduct(editingId, payload);
      } else {
        await createProduct({ product_id: form.product_id, active: true, ...payload });
      }
      resetForm();
      await load();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to save product");
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(product: Product) {
    setSaving(true);
    try {
      await updateProduct(product.product_id, { active: !product.active });
      await load();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to update product");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <header className="pageHeader">
        <div>
          <p className="eyebrow">Configuration</p>
          <h1>Products</h1>
          <p className="summary">
            Platform-owned product configuration consumed by later Buyer Discovery milestones.
          </p>
        </div>
        <button onClick={() => void load()} type="button">
          Refresh
        </button>
      </header>

      {error ? <div className="alert">{error}</div> : null}

      <section className="panel">
        <div className="panelHeader">
          <h2>{editingId ? "Edit Product" : "Create Product"}</h2>
          {editingId ? (
            <button onClick={resetForm} type="button">
              Cancel
            </button>
          ) : null}
        </div>
        <div className="formGrid">
          <label>
            Product ID
            <input
              disabled={Boolean(editingId)}
              onChange={(event) => setForm({ ...form, product_id: event.target.value })}
              value={form.product_id}
            />
          </label>
          <label>
            Category
            <input onChange={(event) => setForm({ ...form, category: event.target.value })} value={form.category} />
          </label>
          <label>
            Name
            <input onChange={(event) => setForm({ ...form, name: event.target.value })} value={form.name} />
          </label>
          <label>
            Priority
            <input
              min="0"
              onChange={(event) => setForm({ ...form, priority: event.target.value })}
              type="number"
              value={form.priority}
            />
          </label>
          <label>
            Aliases
            <input onChange={(event) => setForm({ ...form, aliases: event.target.value })} value={form.aliases} />
          </label>
          <label>
            Variants
            <input onChange={(event) => setForm({ ...form, variants: event.target.value })} value={form.variants} />
          </label>
          <label>
            HS Codes
            <input onChange={(event) => setForm({ ...form, hs_codes: event.target.value })} value={form.hs_codes} />
          </label>
          <div className="formActions">
            <button disabled={saving} onClick={() => void submit()} type="button">
              {editingId ? "Save Product" : "Create Product"}
            </button>
          </div>
        </div>
      </section>

      <section className="panel">
        {loading ? (
          <p className="emptyState">Loading products...</p>
        ) : sortedProducts.length === 0 ? (
          <p className="emptyState">No products configured.</p>
        ) : (
          <div className="tableWrap">
            <table>
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Name</th>
                  <th>Aliases</th>
                  <th>Variants</th>
                  <th>HS Codes</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedProducts.map((product) => (
                  <tr key={product.product_id}>
                    <td>{product.category}</td>
                    <td>
                      <strong>{product.name}</strong>
                      <div className="mutedText">{product.product_id}</div>
                    </td>
                    <td>{joinList(product.aliases)}</td>
                    <td>{joinList(product.variants)}</td>
                    <td>{joinList(product.hs_codes)}</td>
                    <td>{product.priority}</td>
                    <td>
                      <StatusBadge status={product.active ? "active" : "disabled"} />
                    </td>
                    <td>
                      <div className="rowActions">
                        <button onClick={() => edit(product)} type="button">
                          Edit
                        </button>
                        <button disabled={saving} onClick={() => void toggleActive(product)} type="button">
                          {product.active ? "Deactivate" : "Activate"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
