
import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="Customer Purchase Pattern Analysis",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Customer Purchase Pattern Analysis")
st.caption(
    "Big Data Analytics using Java Hadoop MapReduce and Cloud Storage"
)

REQUIRED_COLUMNS = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]


# --------------------------------------------------
# DATA LOADING AND PREPARATION
# --------------------------------------------------
@st.cache_data
def load_csv(file_bytes):
    return pd.read_csv(
        BytesIO(file_bytes),
        encoding="ISO-8859-1"
    )


def prepare_data(data):
    data = data.copy()
    data.columns = data.columns.astype(str).str.strip()

    # Validate columns without regard to capitalization.
    column_lookup = {column.lower(): column for column in data.columns}

    missing = [
        column for column in REQUIRED_COLUMNS
        if column.lower() not in column_lookup
    ]

    if missing:
        return None, missing

    # Standardize expected column names.
    data = data.rename(
        columns={
            column_lookup[column.lower()]: column
            for column in REQUIRED_COLUMNS
        }
    )

    # Convert data types.
    data["InvoiceDate"] = pd.to_datetime(
        data["InvoiceDate"],
        errors="coerce"
    )

    data["Quantity"] = pd.to_numeric(
        data["Quantity"],
        errors="coerce"
    )

    data["UnitPrice"] = pd.to_numeric(
        data["UnitPrice"],
        errors="coerce"
    )

    data["Revenue"] = data["Quantity"] * data["UnitPrice"]

    return data, []


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------
if "retail_df" not in st.session_state:
    st.session_state["retail_df"] = None


# --------------------------------------------------
# SIDEBAR NAVIGATION
# --------------------------------------------------
st.sidebar.header("Project Navigation")

page = st.sidebar.radio(
    "Choose a page",
    [
        "Dashboard",
        "Upload Dataset",
        "Analysis Results",
        "About Project"
    ]
)


# --------------------------------------------------
# UPLOAD DATASET PAGE
# --------------------------------------------------
if page == "Upload Dataset":

    st.subheader("Upload Retail Dataset")

    st.write(
        "Upload a retail transaction CSV file to inspect its "
        "structure before running the analysis."
    )

    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        key="retail_csv"
    )

    if uploaded_file is not None:

        try:
            df, missing_columns = prepare_data(
                load_csv(uploaded_file.getvalue())
            )

            if missing_columns:
                st.error(
                    "Expected columns missing: "
                    + ", ".join(missing_columns)
                )

            else:
                st.session_state["retail_df"] = df

                st.success("CSV file loaded successfully!")

                # Dataset overview
                st.subheader("Dataset Overview")

                col1, col2, col3 = st.columns(3)

                col1.metric("Rows", f"{len(df):,}")
                col2.metric("Columns", len(REQUIRED_COLUMNS))

                missing_values = int(
                    df[REQUIRED_COLUMNS].isna().sum().sum()
                )

                col3.metric(
                    "Missing Values",
                    f"{missing_values:,}"
                )

                # Column validation
                st.subheader("Column Validation")

                st.success(
                    "All expected retail columns are present."
                )

                # Preview
                st.subheader("Preview: First 10 Records")

                st.dataframe(
                    df[REQUIRED_COLUMNS].head(10),
                    use_container_width=True
                )

                # Data types
                st.subheader("Column Data Types")

                types_df = pd.DataFrame({
                    "Column": df.columns.astype(str),
                    "Data Type": df.dtypes.astype(str).values,
                    "Missing Values": df.isna().sum().values,
                })

                st.dataframe(
                    types_df,
                    use_container_width=True
                )

                # Download original uploaded data
                st.download_button(
                    "Download Uploaded CSV",
                    data=uploaded_file.getvalue(),
                    file_name=uploaded_file.name,
                    mime="text/csv"
                )

        except Exception as e:
            st.error(f"Could not read the CSV file: {e}")


# --------------------------------------------------
# DASHBOARD PAGE
# --------------------------------------------------
elif page == "Dashboard":

    st.subheader("Retail Analytics Dashboard")

    df = st.session_state.get("retail_df")

    if df is None:

        st.info(
            "Please open Upload Dataset and upload "
            "online_retail.csv first."
        )

        st.subheader("Analysis Modules")

        left, right = st.columns(2)

        with left:
            st.markdown("**Product Analysis**")
            st.write(
                "Identify best-selling products and sales quantities."
            )

            st.markdown("**Customer Analysis**")
            st.write(
                "Explore customer spending and purchasing behaviour."
            )

        with right:
            st.markdown("**Product Combinations**")
            st.write(
                "Find products purchased together."
            )

            st.markdown("**Purchase Time Analysis**")
            st.write(
                "Explore transaction activity by hour."
            )

    else:

        # Country filter
        st.sidebar.subheader("Dashboard Filters")

        country_list = sorted(
            df["Country"].dropna().unique().tolist()
        )

        selected_countries = st.sidebar.multiselect(
            "Select Countries",
            country_list,
            default=(
                ["United Kingdom"]
                if "United Kingdom" in country_list
                else []
            )
        )

        # Date filter
        valid_dates = df["InvoiceDate"].dropna()

        filtered_df = df.copy()

        if selected_countries:
            filtered_df = filtered_df[
                filtered_df["Country"].isin(selected_countries)
            ]

        if not valid_dates.empty:

            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()

            date_range = st.sidebar.date_input(
                "Select Invoice Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )

            if isinstance(date_range, (tuple, list)) and len(date_range) == 2:

                start_date, end_date = date_range

                filtered_df = filtered_df[
                    filtered_df["InvoiceDate"].dt.date.between(
                        start_date,
                        end_date
                    )
                ]

        # Exclude cancellations and invalid sales from KPIs.
        sales_df = filtered_df[
            filtered_df["InvoiceNo"].notna()
            & ~filtered_df["InvoiceNo"].astype(str).str.startswith("C")
            & (filtered_df["Quantity"] > 0)
            & (filtered_df["UnitPrice"] > 0)
        ].copy()

        # Recalculate revenue for valid sales.
        sales_df["Revenue"] = (
            sales_df["Quantity"] * sales_df["UnitPrice"]
        )

        st.subheader("Business Performance Indicators")

        total_revenue = sales_df["Revenue"].sum()

        total_transactions = sales_df["InvoiceNo"].nunique()

        total_customers = sales_df["CustomerID"].nunique()

        total_products = sales_df["StockCode"].nunique()

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Total Revenue",
            f"£{total_revenue:,.2f}"
        )

        col2.metric(
            "Transactions",
            f"{total_transactions:,}"
        )

        col3.metric(
            "Unique Customers",
            f"{total_customers:,}"
        )

        col4.metric(
            "Products",
            f"{total_products:,}"
        )

        if sales_df.empty:

            st.warning(
                "No valid sales records match the selected filters."
            )

        else:

            # ------------------------------------------
            # MONTHLY REVENUE
            # ------------------------------------------
            st.subheader("Monthly Revenue Trend")

            dated_sales = sales_df.dropna(
                subset=["InvoiceDate"]
            ).copy()

            if not dated_sales.empty:

                dated_sales["Month"] = (
                    dated_sales["InvoiceDate"]
                    .dt.to_period("M")
                    .astype(str)
                )

                monthly_sales = (
                    dated_sales.groupby("Month", as_index=False)
                    ["Revenue"]
                    .sum()
                    .sort_values("Month")
                )

                fig = px.line(
                    monthly_sales,
                    x="Month",
                    y="Revenue",
                    markers=True,
                    title="Revenue by Month"
                )

                fig.update_layout(
                    xaxis_title="Month",
                    yaxis_title="Revenue (£)"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            # ------------------------------------------
            # TOP PRODUCTS AND COUNTRIES
            # ------------------------------------------
            left, right = st.columns(2)

            with left:

                st.subheader("Top 10 Products by Revenue")

                top_products = (
                    sales_df.groupby("Description")["Revenue"]
                    .sum()
                    .nlargest(10)
                    .reset_index()
                )

                if not top_products.empty:

                    fig = px.bar(
                        top_products.sort_values("Revenue"),
                        x="Revenue",
                        y="Description",
                        orientation="h",
                        title="Best-Selling Products"
                    )

                    fig.update_layout(
                        xaxis_title="Revenue (£)",
                        yaxis_title="Product",
                        yaxis={
                            "categoryorder": "total ascending"
                        }
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )

            with right:

                st.subheader("Top 10 Countries by Revenue")

                top_countries = (
                    sales_df.groupby("Country")["Revenue"]
                    .sum()
                    .nlargest(10)
                    .reset_index()
                )

                if not top_countries.empty:

                    fig = px.bar(
                        top_countries,
                        x="Country",
                        y="Revenue",
                        title="Country Sales Performance"
                    )

                    fig.update_layout(
                        xaxis_title="Country",
                        yaxis_title="Revenue (£)"
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )

            # ------------------------------------------
            # TOP CUSTOMERS
            # ------------------------------------------
            st.subheader("Top 10 Customers by Spending")

            customer_df = sales_df.dropna(
                subset=["CustomerID"]
            )

            top_customers = (
                customer_df.groupby("CustomerID")["Revenue"]
                .sum()
                .nlargest(10)
                .reset_index()
            )

            if not top_customers.empty:

                top_customers["CustomerID"] = (
                    top_customers["CustomerID"].astype(str)
                )

                fig = px.bar(
                    top_customers.sort_values("Revenue"),
                    x="Revenue",
                    y="CustomerID",
                    orientation="h",
                    title="Highest-Spending Customers"
                )

                fig.update_layout(
                    xaxis_title="Revenue (£)",
                    yaxis_title="Customer ID",
                    yaxis={
                        "categoryorder": "total ascending"
                    }
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            # ------------------------------------------
            # TRANSACTION PREVIEW
            # ------------------------------------------
            st.subheader("Filtered Transaction Preview")

            st.dataframe(
                filtered_df[REQUIRED_COLUMNS].head(100),
                use_container_width=True
            )

            # ------------------------------------------
            # EXPORT FILTERED DATA
            # ------------------------------------------
            st.download_button(
                "Download Filtered Dataset",
                data=filtered_df.to_csv(
                    index=False
                ).encode("utf-8"),
                file_name="filtered_retail_data.csv",
                mime="text/csv"
            )


# --------------------------------------------------
# ANALYSIS RESULTS PAGE
# --------------------------------------------------
elif page == "Analysis Results":

    st.subheader("MapReduce Analysis Results")

    st.info(
        "Hadoop results will appear here after we implement "
        "and run the Java MapReduce jobs."
    )

    if st.session_state.get("retail_df") is not None:
        st.success(
            "Retail dataset is loaded and ready for further analysis."
        )
    else:
        st.warning(
            "Upload the retail dataset before running the analysis."
        )


# --------------------------------------------------
# ABOUT PROJECT PAGE
# --------------------------------------------------
elif page == "About Project":

    st.subheader("About This Project")

    st.write(
        "This project analyzes retail customer purchase patterns "
        "using Python, Streamlit, Java Hadoop MapReduce, "
        "and cloud storage."
    )

    st.markdown("""
    **Project Objectives**

    - Analyze product sales and revenue.
    - Calculate customer spending.
    - Identify products frequently purchased together.
    - Study transaction activity by hour.
    - Segment customers by spending.
    - Compare Python analytics with Hadoop MapReduce results.
    """)

    st.markdown("""
    **Technology Stack**

    - Python and Pandas
    - Streamlit
    - Plotly
    - Java
    - Apache Hadoop MapReduce
    - Cloud storage (planned)
    """)
