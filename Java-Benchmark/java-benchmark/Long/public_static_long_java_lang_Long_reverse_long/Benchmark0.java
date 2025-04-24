

public class Benchmark0 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Long.reverse(input_1_0);
        Long output_2 = Long.reverse(input_2_0);

        
        // Compare output
        if (output_1 == 6416535454933319680L && output_2 == 9157929104769548287L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

