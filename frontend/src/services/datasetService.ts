import api from './api';

export interface TableInspection {
  table_name: string;
  catalog: string;
  schema_name: string;
  columns: Array<{ name: string; data_type: string; nullable: boolean }>;
  total_rows?: number;
}

export const datasetService = {
  async listTables(catalog?: string, schema?: string) {
    const params = { catalog, schema };
    const res = await api.get('/datasets/tables', { params });
    return res.data;
  },

  async inspectTable(tableName: string, catalog?: string, schema?: string): Promise<TableInspection> {
    const res = await api.post('/datasets/inspect', {
      table_name: tableName,
      catalog,
      schema_name: schema,
    });
    return res.data;
  },

  async cleanData(records: Array<Record<string, unknown>>) {
    const res = await api.post('/datasets/clean', {
      records,
      strip_whitespace: true,
      impute_nulls: true,
    });
    return res.data;
  },
};
