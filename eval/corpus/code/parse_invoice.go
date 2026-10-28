package billing

import (
	"encoding/csv"
	"io"
	"strconv"
)

// ParseInvoiceCSV reads rows of sku,quantity,unit_cents and returns the total in cents.
func ParseInvoiceCSV(r io.Reader) (int64, error) {
	rows, err := csv.NewReader(r).ReadAll()
	if err != nil {
		return 0, err
	}
	var total int64
	for _, row := range rows[1:] {
		qty, _ := strconv.ParseInt(row[1], 10, 64)
		cents, _ := strconv.ParseInt(row[2], 10, 64)
		total += qty * cents
	}
	return total, nil
}
